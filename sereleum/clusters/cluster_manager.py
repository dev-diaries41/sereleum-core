import asyncio 
import numpy as np
import math

from sqlalchemy.exc import IntegrityError

from numpy.typing import NDArray
from abc import abstractmethod
from typing import List, Dict, Generic, TypeVar

from smartscan import Cluster, ClusterMetadata, ClusterMerges, ClusterId, StoredEmbedding, ClusterResult, Assignments
from smartscan.embeds import EmbeddingStore, generate_prototype_embedding
from smartscan.cluster import IncrementalClusterer

from llm_connect.providers.llm_provider import LLMProvider

from sereleum.schemas.llm import LLMClassificationResult
from sereleum.data.clusters.base_cluster_crossrefs_store import BaseClusterCrossRefStore
from sereleum.data.base_store import BaseStore
from sereleum.data.clusters.base_cluster_store import BaseClusterStore
from sereleum.schemas.cluster import ClusterCrossRef, StoredClusterMetadata, ClusterCrossRefFilter
from sereleum.errors import SereleumError, ErrorCode
from sereleum.data.types import  TCrossRefModel, TClusterModel


TItemStore = TypeVar("TItemStore", bound=BaseStore)

class ClusterManager(Generic[TItemStore, TClusterModel, TCrossRefModel]):
    def __init__(self, 
        cluster_embedding_store: EmbeddingStore,
        cluster_store: BaseClusterStore[TClusterModel],
        crossrefs_store: BaseClusterCrossRefStore[TCrossRefModel],
        item_embedding_store: EmbeddingStore,
        item_store: TItemStore,
        llm: LLMProvider, 
        label_confidence_threshold: float = 0.8,
        label_concurrency: int = 8
        ): 
        self.cluster_embedding_store = cluster_embedding_store 
        self.cluster_store = cluster_store
        self.crossrefs_store = crossrefs_store 
        self.llm = llm
        self.label_confidence_threshold = label_confidence_threshold
        self.label_concurrency = label_concurrency
        self.item_store = item_store
        self.item_embedding_store = item_embedding_store

                
    async def cluster(self, auto_label: bool = True, default_threshold: float = 0.3) -> ClusterResult:
        uncluster_embeds = await self._get_unclustered_items()
        if not uncluster_embeds: return ClusterResult()
        clusters_orm = await self.cluster_store.get()
        all_meta = self.from_cluster_orm_list(clusters_orm)
        all_cluster_embeds = await self.cluster_embedding_store.get()
        existing_clusters = { emb.item_id: Cluster(
            prototype_id=emb.item_id,
            embedding=emb.embedding,
            metadata=ClusterMetadata(
                prototype_size=meta.prototype_size,
                mean_similarity=meta.mean_similarity,
                std_similarity=meta.std_similarity,
                label=meta.label
            )
        ) for emb, meta in zip(all_cluster_embeds, all_meta)}
        ## TODO: sample run to get default threshold if existing clusters dont exist
        threshold = self._get_default_threshold(all_meta) if existing_clusters else default_threshold
        clusterer = IncrementalClusterer(
            default_threshold=threshold,
            existing_clusters=existing_clusters,
        )
        result = clusterer.cluster(uncluster_embeds)
        unlabelled = await self._update_clusters_and_assisgn(result, set(existing_clusters.keys()))
        if len(unlabelled) > 0 and auto_label:
           await self.label_and_update(unlabelled)
        return result

    
    async def assign(self, assignments: Assignments) -> None:        
        crossrefs = [ClusterCrossRef(item_id=item_id, cluster_id=cluster_id) for item_id, cluster_id in assignments.items()]
        try:
            await self.crossrefs_store.add(self.to_crossref_orm_list(crossrefs))
        except IntegrityError as e:
            raise SereleumError(
                    "Foreign key violation in assign",
                    code=ErrorCode.INVALID_ARGUMENT,
                    details={"error": str(e)},
                )

    @abstractmethod
    async def label(self, cluster_id: str, sample_size: int) -> LLMClassificationResult:
        raise NotImplementedError
    

    async def label_and_update(self, unlabelled_clusters: List[StoredClusterMetadata], sample_size: int = 10) -> int:
        sem = asyncio.Semaphore(self.label_concurrency)
        label_tasks = {cluster.id: self._label_with_sem(sem, cluster.id, sample_size) for cluster in unlabelled_clusters}
        label_results = {}
        
        if label_tasks:
            results = await asyncio.gather(*label_tasks.values(), return_exceptions=True)
            label_results = dict(zip(label_tasks.keys(), results))
        
        labelled_clusters: list[StoredClusterMetadata] = []
        
        for cluster in unlabelled_clusters:
            result = label_results[cluster.item_id]
            if isinstance(result, Exception):
                print(f"[WARNING] Error labelling {cluster.item_id} | Details: {result}")
            else:
                if result.confidence < self.label_confidence_threshold:
                    print(f"[WARNING] Cluster {cluster.item_id} not labelled | Details: Below confidence threshold: confidence={result.confidence}")
                    continue
                cluster.label = result.label
                labelled_clusters.append(cluster)

        await self.cluster_store.update(self.to_cluster_orm_list(labelled_clusters))
        return len(labelled_clusters)
    

    async def update_label(self, cluster_id: str, label: str) -> bool:
        result = await self.cluster_store.get_by_ids([cluster_id])
        if(len(result)) == 0: return False
        cluster_orm=result[0]
        metadata = self.from_cluster_orm(cluster_orm)
        metadata.label = label
        await self.cluster_store.update([self.to_cluster_orm(metadata)])
        return True

    async def merge(self, merges: ClusterMerges) -> List[StoredClusterMetadata]:
        await self._assign_from_merges(merges)
        merged_clustered_ids = {cid for targets in merges.values() for cid in targets}
        await self.cluster_embedding_store.delete(list(merged_clustered_ids)) 
        await self.crossrefs_store.delete(list(merged_clustered_ids)) 

        cluster_metadata_updates: list[StoredClusterMetadata] = []
        cluster_embed_updates: list[StoredEmbedding] = []

        for merge_id in merges.keys():
            if sync_result := await self._sync(merge_id):
                stored_embed, meta = sync_result
                cluster_embed_updates.append(stored_embed)
                cluster_metadata_updates.append(meta)
            
        await self.cluster_embedding_store.update(cluster_embed_updates)
        await self.cluster_store.update(self.to_cluster_orm_list(cluster_metadata_updates))
        return cluster_metadata_updates
     

    async def get_top_clusters(self, n: int) -> List[StoredClusterMetadata]:
        results =  await self.cluster_store.get(order_by="prototype_size", ascending=False, limit=n)
        return self.from_cluster_orm_list(results)


    async def _assign_from_merges(self, merges: ClusterMerges) -> None:
        all_target_cluster_ids = [cid for targets in merges.values() for cid in targets]
        cross_refs: list[ClusterCrossRef] = []

        for crossref_orm in await self.crossrefs_store.get(filter=ClusterCrossRefFilter(include_cluster_ids=all_target_cluster_ids)):
            crossref = self.from_crossref_orm(crossref_orm)
            original_cluster = crossref.cluster_id
            new_cluster_id = next(
                (mid for mid, clusters in merges.items()
                if original_cluster in clusters),
                original_cluster,
            )
            crossref.cluster_id = new_cluster_id
            cross_refs.append(crossref)

        await self.crossrefs_store.update(self.to_crossref_orm_list(cross_refs))

    # MUST update clusters firsts before assignments!!!
    async def _update_clusters_and_assisgn(self, result: ClusterResult, existing_clusters_ids: set[str]) -> List[StoredClusterMetadata]:
        new_cluster_metadata_updates: list[StoredClusterMetadata] = []
        existing_cluster_metadata_updates: list[StoredClusterMetadata] = []
        new_cluster_embed_updates: list[StoredEmbedding] = []
        existing_cluster_embed_updates: list[StoredEmbedding] = []
        unlabelled_clusters: list[StoredClusterMetadata] = []

        for cluster in result.clusters.values():
            updated_meta = StoredClusterMetadata(
                id=cluster.prototype_id,
                prototype_size=cluster.metadata.prototype_size,
                mean_similarity=cluster.metadata.mean_similarity,
                std_similarity=cluster.metadata.std_similarity,
                label = cluster.metadata.label,
            )
            stored_embed = StoredEmbedding(item_id=updated_meta.id, embedding=cluster.embedding)

            if updated_meta.id in existing_clusters_ids:
                existing_cluster_embed_updates.append(stored_embed)
                existing_cluster_metadata_updates.append(updated_meta)
            else:
                new_cluster_embed_updates.append(stored_embed)
                new_cluster_metadata_updates.append(updated_meta)
            
            if cluster.metadata.label== Cluster.UNLABELLED:
                unlabelled_clusters.append(updated_meta)
             
        await self.cluster_store.update(self.to_cluster_orm_list(existing_cluster_metadata_updates))
        await self.cluster_store.add(self.to_cluster_orm_list(new_cluster_metadata_updates))
        await self.cluster_embedding_store.update(existing_cluster_embed_updates)
        await self.cluster_embedding_store.add(new_cluster_embed_updates)
        await self.assign(result.assignments)
        return unlabelled_clusters

    async def _sync(self, cluster_id: ClusterId) -> tuple[StoredEmbedding, StoredClusterMetadata] | None:
        result = await self.cluster_store.get_by_ids([cluster_id])
        if len(result) == 0:
            return None
        crossrefs_orm = await self.crossrefs_store.get(filter=ClusterCrossRefFilter(include_cluster_ids=[cluster_id]))
        crossrefs = self.from_crossref_orm_list(crossrefs_orm)
        if len(crossrefs) == 0:
            await self.cluster_store.delete([cluster_id])
            return None
        item_ids = [c.item_id for c in crossrefs]
        embeds = await self.item_embedding_store.get(ids=item_ids)
        new_protoype_embed, new_mean_sim, new_std_sim = self._compute_cluster_metrics(np.stack([e.embedding for e in embeds], axis=0))
        
        old_cluster_metadata = self.from_cluster_orm(result[0])
        new_meta = StoredClusterMetadata(
            id = old_cluster_metadata.id,
            prototype_size=len(embeds),
            mean_similarity=new_mean_sim,
            std_similarity=new_std_sim,
            label = old_cluster_metadata.label
            )
        stored_embed = StoredEmbedding(item_id=new_meta.id, embedding=new_protoype_embed)
        return stored_embed, new_meta
    
    async def _get_unclustered_items(self) -> Dict[str, NDArray]:
        unclustered_items_ids = await self.get_unclustered_item_ids()
        print(f"Unclustered items: {len(unclustered_items_ids)}")
        if len(unclustered_items_ids) == 0:
            return {}
        unclustered_item_embeds  = await self.item_embedding_store.get(unclustered_items_ids)
        return {emb.item_id: emb.embedding for emb in unclustered_item_embeds}

    def _compute_cluster_metrics(self, embeds: List[NDArray]):
        new_protoype_embed = generate_prototype_embedding(embeds)
        sims = np.dot(embeds, new_protoype_embed)
        new_mean_sim = float(np.mean(sims))
        new_std_sim = math.sqrt(np.mean([(float(sim) - new_mean_sim)**2 for sim in sims]))
        return new_protoype_embed, new_mean_sim, new_std_sim

    def _get_default_threshold(self, existing_clusters: List[StoredClusterMetadata]) -> float:
        return float(np.mean([(c.mean_similarity - c.std_similarity) for c in existing_clusters]))
    
    async def _label_with_sem(self, semaphore:  asyncio.Semaphore, cluster_id: str, sample_size: int) -> LLMClassificationResult:
        async with semaphore:
            return await self.label(cluster_id, sample_size)
        

    # Used so to avoid having to load all stored embeds and then crossrefs
    @abstractmethod
    async def get_unclustered_item_ids(self) -> List[str]:
        ...

    @abstractmethod
    def to_cluster_orm(self, cluster: StoredClusterMetadata)-> TClusterModel:
        ...

    @abstractmethod
    def to_crossref_orm(self, crossref: ClusterCrossRef) -> TCrossRefModel:
        ...

    @abstractmethod
    def from_cluster_orm(self, cluster_orm: TClusterModel)-> StoredClusterMetadata:
        ...

    @abstractmethod
    def from_crossref_orm(self, crossref_orm: TCrossRefModel) -> ClusterCrossRef:
        ...

    def from_cluster_orm_list(self, clusters_orm: List[TClusterModel])-> List[StoredClusterMetadata]:
        return [self.from_cluster_orm(c) for c in clusters_orm]

    def to_cluster_orm_list(self, clusters: List[StoredClusterMetadata])-> List[TClusterModel]:
        return [self.to_cluster_orm(c) for c in clusters]

    
    def from_crossref_orm_list(self, crossrefs_orm: List[TCrossRefModel])-> List[ClusterCrossRef]:
        return [self.from_crossref_orm(c) for c in crossrefs_orm]

    def to_crossref_orm_list(self, crossrefs: List[ClusterCrossRef])-> List[TCrossRefModel]:
        return [self.to_crossref_orm(c) for c in crossrefs]