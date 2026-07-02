import asyncio 
import numpy as np
import math
from typing import List, Dict, Optional, Generic

from smartscan import ItemEmbedding, Cluster, ClusterNoEmbeddings, ClusterMetadata, ClusterMerges, ClusterId, ItemEmbeddingUpdate, Include, GetResult, QueryResult, ClusterResult
from smartscan.embeds import EmbeddingStore, generate_prototype_embedding
from smartscan.cluster import IncrementalClusterer

from llm_connect.providers.llm_provider import LLMProvider

from sereleum.schemas.llm import LLMClassificationResult
from sereleum.items.item_manager import ItemManager
from sereleum.store.helpers import   paginate_until
from sereleum.schemas.items.item import TData, TItem, TMetadata

from abc import abstractmethod

class ClusterManager(Generic[TItem, TData, TMetadata]):
    def __init__(self, 
        embedding_store: EmbeddingStore,
        items_manager: ItemManager[TItem, TData, TMetadata],
        llm: LLMProvider, 
        label_confidence_threshold: float = 0.8,
        label_concurrency: int = 8,
                 ): 
        self.embedding_store = embedding_store 
        self.items_manager = items_manager
        self.llm = llm
        self.label_confidence_threshold = label_confidence_threshold
        self.label_concurrency = label_concurrency
    
    async def cluster(self, auto_label: bool = True, default_threshold: float = 0.3) -> List[ItemEmbeddingUpdate[None, ClusterMetadata]]:
        ids, _, embeddings = self.items_manager.get_samples(1e5, exclude_clustered=True)
        existing_clusters = self.get_all_clusters()
        threshold = self._get_default_threshold(List(existing_clusters.values())) if existing_clusters else default_threshold
        clusterer = IncrementalClusterer(
            default_threshold=threshold,
            existing_clusters=existing_clusters,
        )
        result = clusterer.cluster(ids, embeddings)
        unlabelled = await self._update_from_result(result)
        if len(unlabelled) > 0 and auto_label:
           await self.label_and_update(unlabelled)
        return unlabelled

    
    @abstractmethod
    def label(self, cluster_id: str, sample_size: int) -> LLMClassificationResult:
        raise NotImplementedError
    
    async def async_label(self, semaphore:  asyncio.Semaphore, cluster_id: str, sample_size: int) -> LLMClassificationResult:
        async with semaphore:
            return await asyncio.to_thread(self.label, cluster_id, sample_size)


    async def label_and_update(self, unlabelled_clusters: List[ItemEmbeddingUpdate[None, ClusterMetadata]], sample_size: int = 10) -> int:
        sem = asyncio.Semaphore(self.label_concurrency)
        label_tasks = {cluster.item_id: self.async_label(sem, cluster.item_id, sample_size) for cluster in unlabelled_clusters}
        label_results = {}
        
        if label_tasks:
            results = await asyncio.gather(*label_tasks.values(), return_exceptions=True)
            label_results = dict(zip(label_tasks.keys(), results))
        
        labelled_clusters: list[ItemEmbeddingUpdate[None, ClusterMetadata]] = []
        
        for cluster in unlabelled_clusters:
            result = label_results[cluster.item_id]
            if isinstance(result, Exception):
                print(f"[WARNING] Error labelling {cluster.item_id} | Details: {result}")
            else:
                if result.confidence < self.label_confidence_threshold:
                    print(f"[WARNING] Cluster {cluster.item_id} not labelled | Details: Below confidence threshold: confidence={result.confidence}")
                    continue
                cluster.metadata['label'] = result.label
                labelled_clusters.append(cluster)

        if len(labelled_clusters) > 0:
            self.embedding_store.update(labelled_clusters)

        return len(labelled_clusters)
    

    def update_label(self, cluster_id: str, label: str) -> bool:
        result = self.get_clusters(cluster_ids=[cluster_id], include=['metadatas'])
        if(len(result)) == 0: return False
        updated_meta=result[cluster_id].metadata
        updated_meta.label = label
        updated_cluster = ItemEmbeddingUpdate(item_id=cluster_id, metadata=updated_meta.model_dump())
        self.embedding_store.update([updated_cluster])
        return True

    def merge(self, merges: ClusterMerges) -> List[ClusterNoEmbeddings]:
        self.items_manager.reassign_from_merges(merges)
        merged_clustered_ids = {cid for targets in merges.values() for cid in targets}
        self.embedding_store.delete(list(merged_clustered_ids)) 
        updated_clusters: List[ItemEmbedding[None, ClusterMetadata]] = []

        for merge_id in merges.keys():
            cluster = self._sync(merge_id)
            updated_clusters.append(cluster)
        self.embedding_store.upsert(updated_clusters)

        return self._to_clusters_from_item_embeddings(updated_clusters, with_embeddings=False)
    
    def query(self, query_embed: np.ndarray, cluster_ids: Optional[List[str]] = None, limit: int = 10) -> (Dict[ClusterId, Cluster] | Dict[ClusterId, ClusterNoEmbeddings]):
        result = self.embedding_store.query(
            query_embeds=[query_embed], 
            limit=limit, 
                filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None,
            include=["metadatas"]
            )
        return self._to_clusters_dict(result)
    
    def get_existing_labels(self, batch_size: int = 100) -> list[str]:
        labels: list[str] = []
        for batch in paginate_until(
            fetch_fn=lambda offset, limit: self.embedding_store.get(
                include=['metadatas'], filter={"label": {"$ne": Cluster.UNLABELLED}},
                limit=limit,
                offset=offset
                ),
            break_fn=lambda batch: len(batch.metadatas) == 0,
            batch_size=batch_size,
            ):
            labels.extend([m.get("label") for m in batch.metadatas])
        return labels
    

    def get_clusters(self, cluster_ids: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None, include: Optional[Include] = None) -> dict[ClusterId, Cluster | ClusterNoEmbeddings]:
        include = include or []
        if 'metadatas' not in include:
            include.append('metadatas')

        results = self.embedding_store.get(
                ids = cluster_ids if cluster_ids else None,
                include=include,
                limit=limit,
                offset=offset
                )
        if "embeddings" in include:
            return self._to_clusters_dict(results, with_embeddings=True)
        else:
            return self._to_clusters_dict(results, with_embeddings=False)

    
    def get_all_clusters(self) -> dict[ClusterId, Cluster]:
        clusters: Dict[ClusterId, Cluster] = {}
        for batch in paginate_until(
            fetch_fn=lambda offset, limit: self.embedding_store.get(
                include=['metadatas', 'embeddings'],
                limit=limit,
                offset=offset
                ),
            break_fn=lambda batch: len(batch.metadatas) == 0,
            batch_size=500
            ):
            clusters.update(self._to_clusters_dict(batch, with_embeddings=True))
        return clusters
    

    def get_top_clusters(self, n: int) -> Dict[ClusterId, ClusterNoEmbeddings]:
        top_clusters: Dict[ClusterId, ClusterNoEmbeddings] = {}
        offset = 0
        max_prototype_size = 0
        added_this_pass = True

        while added_this_pass:
            added_this_pass = False
            offset = 0

            while True:
                result = self.embedding_store.get(
                    include=["metadatas"],
                    limit=n,
                    offset=offset,
                    filter={"prototype_size": {"$gt": max_prototype_size}} if max_prototype_size > 0 else None,
                )

                if len(result.metadatas) == 0:
                    break

                clusters_page = self._to_clusters_dict(result)
                for cid, cluster in clusters_page.items():
                    if cid not in top_clusters:
                        top_clusters[cid] = cluster
                        added_this_pass = True

                offset += n

            if added_this_pass:
                # Update max_prototype_size only after a full pass that added new clusters
                max_prototype_size = max(
                    cluster.metadata.prototype_size for cluster in top_clusters.values()
                )

            # Keep only top-n clusters sorted by prototype_size
            if len(top_clusters) > n:
                top_clusters = dict(
                    sorted(
                        top_clusters.items(),
                        key=lambda x: x[1].metadata.prototype_size,
                        reverse=True
                    )[:n]
                )

        return top_clusters
    

    async def _update_from_result(self, result: ClusterResult) -> List[ItemEmbeddingUpdate[None, ClusterMetadata]]:
        self.items_manager.assign(result)
        effective_clusters: Dict[str, Cluster] = result.clusters.copy()

        if result.merges:
            merged_ids = {cid for targets in result.merges.values() for cid in targets}
            for mid in merged_ids:
                effective_clusters.pop(mid, None)
     
        cluster_updates: list[ItemEmbedding[None, ClusterMetadata]] = []
        unlabelled_clusters: list[ItemEmbeddingUpdate[None, ClusterMetadata]] = []

        for cluster in effective_clusters.values():
            updated_cluster = ItemEmbedding[None, ClusterMetadata](
                cluster.prototype_id,
                cluster.embedding,
                metadata={**cluster.metadata.model_dump()} 
            )
            cluster_updates.append(updated_cluster)

            if cluster.label== Cluster.UNLABELLED:
                unlabelled_clusters.append(ItemEmbeddingUpdate(item_id=updated_cluster.item_id, metadata=updated_cluster.metadata, data=updated_cluster.data))
             
        if len(cluster_updates) > 0:
            self.embedding_store.upsert(cluster_updates)
        
        if result.merges:
            clusters_updates_from_merge: List[ItemEmbedding[None, ClusterMetadata]] = []
            for merge_id in result.merges.keys():
                cluster = self._sync(merge_id)
                clusters_updates_from_merge.append(cluster)

            self.embedding_store.upsert(clusters_updates_from_merge)

        return unlabelled_clusters

    def _sync(self, cluster_id: ClusterId) -> ItemEmbedding[None, ClusterMetadata]:
        cluster = self.get_clusters(cluster_ids=[cluster_id], include=['metadatas'])[cluster_id]
        _, _, embeds = self.items_manager.get(cluster_ids=[cluster_id])
        new_protoype_embed, new_mean_sim, new_std_sim = self._compute_cluster_metrics(embeds)
        
        return ItemEmbedding[None, ClusterMetadata](
            item_id = cluster.prototype_id,
            embedding=new_protoype_embed,
            metadata=ClusterMetadata(
                prototype_size=len(embeds),
                mean_similarity=new_mean_sim,
                std_similarity=new_std_sim,
                label = cluster.label
                ).model_dump()
            )

    def _compute_cluster_metrics(self, embeds: List[np.ndarray]):
        new_protoype_embed = generate_prototype_embedding(embeds)
        sims = np.dot(embeds, new_protoype_embed)
        new_mean_sim = float(np.mean(sims))
        new_std_sim = math.sqrt(np.mean([(float(sim) - new_mean_sim)**2 for sim in sims]))
        return new_protoype_embed, new_mean_sim, new_std_sim

    def _get_default_threshold(self, existing_clusters: List[Cluster]) -> float:
        return float(np.mean([(c.metadata.mean_similarity - c.metadata.std_similarity) for c in existing_clusters]))
    
    def _to_clusters_dict(self, results: QueryResult[None, ClusterMetadata] | GetResult[None, ClusterMetadata], with_embeddings: bool = False) -> (Dict[ClusterId, Cluster] | Dict[ClusterId, ClusterNoEmbeddings]):
        if with_embeddings:
           return { cluster_id: Cluster(cluster_id, embedding, ClusterMetadata(**metadata), label=metadata.get("label")) for cluster_id, embedding, metadata in zip(results.ids, results.embeddings, results.metadatas)}
        else:
            return { cluster_id: ClusterNoEmbeddings(prototype_id=cluster_id, metadata=ClusterMetadata(**metadata), label=metadata.get("label")) for cluster_id, metadata in zip(results.ids, results.metadatas)}
        
    def _to_clusters_from_item_embeddings(self, updated_clusters: List[ItemEmbedding[None, ClusterMetadata]] | List [ItemEmbeddingUpdate[None, ClusterMetadata]], with_embeddings: bool = False):
        if with_embeddings:
            return [Cluster(prototype_id=c.item_id, embedding=c.embedding, metadata=c.metadata, label=c.metadata['label']) for c in updated_clusters]
        else:
            return [ClusterNoEmbeddings(prototype_id=c.item_id, metadata=c.metadata, label=c.metadata['label']) for c in updated_clusters]