import asyncio 


import numpy as np
from typing import List, Dict, Optional, Iterable, Tuple

from smartscan import ItemEmbedding, Cluster, ClusterNoEmbeddings, ClusterMetadata, Assignments, ClusterMerges, ItemId, TextEmbeddingProvider, ClusterId, ClusterAccuracy, ItemEmbeddingUpdate, Include, GetResult, QueryResult
from smartscan.classify import  calculate_cluster_accuracy
from smartscan.embeds import EmbeddingStore, generate_prototype_embedding

from sereleum.utils import   paginate_until
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.label import  async_label_prompts
from sereleum.providers.llm.llm_client import LLMClient

class ClustersManager():
    def __init__(self, 
        embedding_store: EmbeddingStore,
        prompts_manager: PromptsManager,
        llm: LLMClient, 
        label_confidence_threshold: float = 0.8,
        label_concurrency: int = 8,
                 ): 
        self.embedding_store = embedding_store 
        self.prompts_manager = prompts_manager
        self.llm = llm
        self.label_confidence_threshold = label_confidence_threshold
        self.label_concurrency = label_concurrency

    
    async def update_clusters(self, clusters: Dict[str, Cluster], merges: ClusterMerges) -> List[ItemEmbeddingUpdate[None, ClusterMetadata]]:
        """
        Update the embedding store with clusters, applying merges if provided.
        Old clusters that have been merged are removed from the store.
        """
        effective_clusters: Dict[str, Cluster] = clusters.copy()

        if merges:
            merged_ids = {cid for targets in merges.values() for cid in targets}
            for mid in merged_ids:
                effective_clusters.pop(mid, None)
     
      
        updated_clusters: list[ItemEmbedding[None, ClusterMetadata]] = []
        unlabelled_clusters: list[ItemEmbeddingUpdate[None, ClusterMetadata]] = []

        for cluster in effective_clusters.values():
            updated_cluster = ItemEmbedding[None, ClusterMetadata](
                cluster.prototype_id,
                cluster.embedding,
                metadata={**cluster.metadata.model_dump()} 
            )
            updated_clusters.append(updated_cluster)

            if cluster.label== Cluster.UNLABELLED:
                unlabelled_clusters.append(ItemEmbeddingUpdate(item_id=updated_cluster.item_id, metadata=updated_cluster.metadata, data=updated_cluster.data))
             
        if merges:
            self.embedding_store.delete(list(merged_ids))

        if len(updated_clusters) > 0:
            self.embedding_store.upsert(updated_clusters)
        
        return unlabelled_clusters
    

    async def label_and_update_clusters(self, unlabelled_clusters: List[ItemEmbeddingUpdate[None, ClusterMetadata]], sample_size: int = 10) -> int:
        existing_labels = self.get_existing_labels()
        sem = asyncio.Semaphore(self.label_concurrency)
        label_tasks = {cluster.item_id: async_label_prompts(sem, self.llm, self.prompts_manager, cluster.item_id, sample_size, existing_labels) for cluster in unlabelled_clusters}
        label_results = {}
        
        if label_tasks:
            results = await asyncio.gather(*label_tasks.values(), return_exceptions=True)
            label_results = dict(zip(label_tasks.keys(), results))
        
        labelled_clusters: list[ItemEmbeddingUpdate[None, ClusterMetadata]] = []
        
        for cluster in unlabelled_clusters:
            if isinstance(label_results[cluster.item_id], Exception):
                print(f"Warning: Error labelling {cluster.item_id}")
            else:
                result = label_results[cluster.item_id]
                if result.confidence < self.label_confidence_threshold:
                    continue
                cluster.metadata['label'] = result.label
                labelled_clusters.append(cluster)

        if len(labelled_clusters) > 0:
            self.embedding_store.update(labelled_clusters)

        return len(labelled_clusters)
    

    def update_cluster_label(self, cluster_id: str, label: str) -> bool:
        """
        Update the embedding store with clusters, applying merges if provided.
        Old clusters that have been merged are removed from the store.
        """
        result = self.get_clusters(cluster_ids=[cluster_id], include=['metadatas'])
        if(len(result)) == 0: return False
        updated_meta=result[cluster_id].metadata
        updated_meta.label = label
        updated_cluster = ItemEmbeddingUpdate(item_id=cluster_id, metadata=updated_meta.model_dump())
        self.embedding_store.update([updated_cluster])
        return True

    def merge_clusters(self, merges: ClusterMerges) -> List[ClusterNoEmbeddings]:
        self.prompts_manager.update_prompts(merges)
        merged_clustered_ids = {cid for targets in merges.values() for cid in targets}
        all_clusters = self.get_all_clusters()

       # MUST happen after get all clusters!!!
        self.embedding_store.delete(list(merged_clustered_ids)) 

        updated_clusters: List[ItemEmbedding[None, ClusterMetadata]] = []

        for merge_id in merges.keys():
            cluster = self.get_clusters(cluster_ids=[merge_id], include=['metadatas'])[merge_id]
            _, _, embeds  = self.prompts_manager.get_prompt_metadata_samples(1e5, cluster_ids=[merge_id])
            new_protoype_embed = generate_prototype_embedding(embeds)
            new_mean_similarity = np.mean(np.dot(embeds, new_protoype_embed))
            new_prototype_size = len(embeds)
            all_cluster_embeds = np.stack([c.embedding for cid, c in all_clusters.items() if cid != merge_id],axis=0)
            nearest_sim = float(np.max(np.dot(all_cluster_embeds, new_protoype_embed)))
            
            updated_clusters.append(
                ItemEmbedding[None, ClusterMetadata](
                item_id = cluster.prototype_id,
                embedding=new_protoype_embed,
                metadata=ClusterMetadata(
                    prototype_size=new_prototype_size,
                    mean_similarity=new_mean_similarity,
                    label = cluster.label,
                    nearest_other_similarity=nearest_sim,
                    separation_margin=new_mean_similarity - nearest_sim
                    ).model_dump()
                    )
                )
        self.embedding_store.upsert(updated_clusters)

        return self._to_clusters_from_item_embeddings(updated_clusters, with_embeddings=False)
    
    def query_clusters(self, text_embedder: TextEmbeddingProvider, query: str, cluster_ids: Optional[List[str]] = None, limit: int = 10) -> (Dict[ClusterId, Cluster] | Dict[ClusterId, ClusterNoEmbeddings]):
        embed = text_embedder.embed(query)
        result = self.embedding_store.query(
            query_embeds=[embed], 
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
    

    def get_clusters(self, cluster_ids: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None, include: Include = ['metadatas', 'embeddings']) -> dict[ClusterId, Cluster | ClusterNoEmbeddings]:
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

        while True:
            max_prototype_size = max(
                (cluster.metadata.prototype_size for cluster in top_clusters.values()),
                default=0,
            )

            result = self.embedding_store.get(
                include=["metadatas"],
                limit=n,
                filter={"prototype_size": {"$gt": max_prototype_size + 1}},
            )

            if len(result.metadatas) == 0:
                break

            if len(result.metadatas) == n:
                top_clusters = self._to_clusters_dict(result)
            else:
                top_clusters.update(self._to_clusters_dict(result))

                if len(top_clusters) > n:
                    top_clusters = dict(
                        sorted(
                            top_clusters.items(),
                            key=lambda x: x[1].metadata.prototype_size,
                            reverse=True,
                        )[:n]
                    )
        return top_clusters
    
    def calculate_avg_tokens_for_cluster(self, cluster_id: str, sample_size: int) -> int:
        total_tokens = 0
        prompts_count = 0

        for _, metadata in self.prompts_manager.stream_prompts_metadata([cluster_id]):
            if prompts_count >= sample_size:
                break
            total_tokens += (metadata.tokens or 0)
            prompts_count += (1 if metadata.tokens else 0)
        return int(total_tokens / max(1, prompts_count))
    

    # TODO: accept prompt_ids that are lablled and fetch label from meta
    #args: ids and label
    def calculate_cluster_accuracy(self) -> ClusterAccuracy:
        true_labels: dict[ItemId, str] = {}
        assignments: Assignments = {}
        for p in  self.prompts_manager.stream_prompts():
            ## temp solution
            assignments[p.prompt_id] = p.metadata.cluster_id
            label = p.prompt_id.split("_")[0]
            if not label: 
                print(f"[WARNING] {p.prompt_id} is not a valid labelled item.")
                continue
            true_labels[p.prompt_id] = label
        return calculate_cluster_accuracy(true_labels, assignments)
    
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

