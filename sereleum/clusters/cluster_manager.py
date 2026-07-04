import asyncio 
import numpy as np
import math

from numpy.typing import NDArray
from abc import abstractmethod
from typing import List, Dict, Generic

from smartscan import Cluster, ClusterMetadata, ClusterMerges, ClusterId, StoredEmbedding, ClusterResult, Assignments
from smartscan.embeds import EmbeddingStore, generate_prototype_embedding
from smartscan.cluster import IncrementalClusterer

from llm_connect.providers.llm_provider import LLMProvider

from sereleum.schemas.llm import LLMClassificationResult
from sereleum.data.clusters.base_cluster_crossrefs_store import BaseClusterCrossRefStore
from sereleum.data.clusters.base_cluster_store import BaseClusterStore
from sereleum.schemas.cluster import ClusterCrossRef, StoredClusterMetadata, ClusterCrossRefFilter
from sereleum.data.base_store import BaseStore
from sereleum.data.types import TItem, TItemFilter

class ClusterManager(Generic[TItem, TItemFilter]):
    def __init__(self, 
        cluster_embedding_store: EmbeddingStore,
        cluster_store: BaseClusterStore,
        crossrefs_store: BaseClusterCrossRefStore,
        item_embedding_store: EmbeddingStore,
        item_store: BaseStore[TItem, TItemFilter],
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
        # TEMP solution instead get clustered items using join
        uncluster_embeds = await self._get_unclustered_items()
        if not uncluster_embeds: return [] 
        all_meta = await self.cluster_store.get()
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
        ## TODO: to sample cluster to get default threshold if existing clusters dont exist
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
        await self.crossrefs_store.update(crossrefs)

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

        await self.cluster_store.update(labelled_clusters)
        return len(labelled_clusters)
    

    async def update_label(self, cluster_id: str, label: str) -> bool:
        result = await self.cluster_store.get_by_ids([cluster_id])
        if(len(result)) == 0: return False
        updated_meta=result[0]
        updated_meta.label = label
        await self.cluster_store.update([updated_meta])
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
        await self.cluster_store.update(cluster_metadata_updates)
        return cluster_metadata_updates
     

    async def get_top_clusters(self, n: int) -> List[StoredClusterMetadata]:
        return await self.cluster_store.get(order_by="prototype_size", ascending=False, limit=n)


    async def _assign_from_merges(self, merges: ClusterMerges) -> None:
        all_target_cluster_ids = [cid for targets in merges.values() for cid in targets]
        cross_refs: list[ClusterCrossRef] = []

        for crossref in await self.crossrefs_store.get(filter=ClusterCrossRefFilter(include_cluster_ids=all_target_cluster_ids)):
            original_cluster = crossref.cluster_id
            new_cluster_id = next(
                (mid for mid, clusters in merges.items()
                if original_cluster in clusters),
                original_cluster,
            )
            crossref.cluster_id = new_cluster_id
            cross_refs.append(crossref)

        self.crossrefs_store.update(cross_refs)

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
             
        await self.cluster_store.update(existing_cluster_metadata_updates)
        await self.cluster_store.add(new_cluster_metadata_updates)
        await self.cluster_embedding_store.update(existing_cluster_embed_updates)
        await self.cluster_embedding_store.add(new_cluster_embed_updates)
        await self.assign(result.assignments)
        return unlabelled_clusters

    async def _sync(self, cluster_id: ClusterId) -> tuple[StoredEmbedding, StoredClusterMetadata] | None:
        result = await self.cluster_store.get_by_ids([cluster_id])
        if len(result) == 0:
            return None
        cluster_metadata = result[0]
        crossrefs = await self.crossrefs_store.get(filter=ClusterCrossRefFilter(include_cluster_ids=[cluster_id]))
        if len(crossrefs) == 0:
            await self.cluster_store.delete([cluster_id])
            return None
        item_ids = [c.item_id for c in crossrefs]
        embeds = await self.item_embedding_store.get(ids=item_ids)
        new_protoype_embed, new_mean_sim, new_std_sim = self._compute_cluster_metrics(np.stack([e.embedding for e in embeds], axis=0))
        
        meta = StoredClusterMetadata(
            id = cluster_metadata.id,
            prototype_size=len(embeds),
            mean_similarity=new_mean_sim,
            std_similarity=new_std_sim,
            label = cluster_metadata.label
            )
        stored_embed = StoredEmbedding(item_id=meta.id, embedding=new_protoype_embed)
        return stored_embed, meta
    
    async def _get_unclustered_items(self) -> Dict[str, NDArray]:
        stored_embeds  = await self.item_embedding_store.get()
        clustered_items = {c.item_id for c in await self.crossrefs_store.get()}
        return {emb.item_id: emb.embedding for emb in stored_embeds if emb.item_id not in clustered_items}

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