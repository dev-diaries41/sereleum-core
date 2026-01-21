import asyncio 

from numpy import ndarray
from datetime import datetime
from typing import List, Dict, Optional, Iterable

from smartscan import ItemEmbedding, Cluster, ClusterMetadata, Assignments, ClusterMerges, ItemId, TextEmbeddingProvider, ClusterId, ClusterAccuracy, ItemEmbeddingUpdate, Include, GetResult, QueryResult
from smartscan.classify import  calculate_cluster_accuracy
from smartscan.embeds import EmbeddingStore

from revelium.schemas.api import ClusterNoEmbeddings
from revelium.types import Prompt, PromptMetadata, PromptsOverviewInfo
from revelium.providers.types import TextEmbeddingModel
from revelium.schemas.llm import LLMClassificationResult
from revelium.providers.llm.llm_client import LLMClient
from revelium.utils import  paginated_read, paginated_read_until_empty
from revelium.tokens import embedding_token_cost
from revelium.errors import ReveliumError, ErrorCode



class PromptsManager():
    CLUSTER_TYPE = "cluster"
    PROMPT_TYPE = "prompt"

    def __init__(self, 
        cluster_embedding_store: EmbeddingStore,
        prompt_embedding_store: EmbeddingStore,
        llm_client: Optional[LLMClient] = None,
                 ): 
        self.llm = llm_client
        self.cluster_embedding_store = cluster_embedding_store 
        self.prompt_embedding_store = prompt_embedding_store
        

    def label_prompts(self, cluster_id: str, sample_size: int, existing_labels: list[str]) -> LLMClassificationResult:
        if not self._has_llm_client():
            raise ReveliumError("No LLM client exists", code=ErrorCode.MISSING_LLM_CLIENT)
        prompts = self.prompt_embedding_store.get(filter={"cluster_id": cluster_id},  limit=sample_size, include=['documents'])
        sample_prompts = [content for content in prompts.datas]
        input_prompt = self._get_labelling_prompt(cluster_id, existing_labels, sample_prompts)
        return self.llm.generate_json(input_prompt, LLMClassificationResult)
                
             
    def update_prompts(self, assignments: Assignments, merges: ClusterMerges) -> None:
        prompt_ids = [str(k) for k in assignments.keys()]
        metadatas = self.get_prompts_metadata(prompt_ids)
        if not metadatas:
            raise ReveliumError("No matching prompts found", code=ErrorCode.PROMPT_NOT_FOUND)
        
        updated_at = datetime.now().isoformat()
        updated_prompts: list[ItemEmbedding] = []

        for prompt_id, metadata in zip(prompt_ids, metadatas):
            original_cluster = assignments[prompt_id]

            if not merges:
                new_cluster = original_cluster
            else:
                new_cluster = next(
                    (mid for mid, clusters in merges.items()
                    if original_cluster in clusters),
                    original_cluster,
                )

            updated_prompts.append(
                ItemEmbeddingUpdate(
                    prompt_id,
                    metadata=PromptMetadata(cluster_id=new_cluster, created_at=metadata.created_at, updated_at=updated_at).model_dump()
                )
            )
        # print(f"length of updated: {len(updated_prompts)}")

        self.prompt_embedding_store.update(updated_prompts)


    async def update_clusters(self, clusters: Dict[str, Cluster], merges: ClusterMerges, label_confidence_threshold: float = 0.8) -> None:
        """
        Update the embedding store with clusters, applying merges if provided.
        Old clusters that have been merged are removed from the store.
        """
        effective_clusters: Dict[str, Cluster] = clusters.copy()

        if merges:
            merged_ids = {cid for targets in merges.values() for cid in targets}
            for mid in merged_ids:
                effective_clusters.pop(mid, None)
        
        existing_labels = self.get_existing_labels()

        sem = asyncio.Semaphore(8)

        async def async_label_prompts(cluster_id):
            async with sem:
                return await asyncio.to_thread(self.label_prompts, cluster_id, 10, existing_labels)

        label_tasks = {
            cluster_id: async_label_prompts(cluster_id)
            for cluster_id, cluster in effective_clusters.items()
            if cluster.label == Cluster.UNLABELLED
        }
        label_results = {}
        if label_tasks:
            results = await asyncio.gather(*label_tasks.values(), return_exceptions=True)
            label_results = dict(zip(label_tasks.keys(), results))

        updates: list[ItemEmbedding[None, ClusterMetadata]] = []
        
        for cluster in effective_clusters.values():
            updated_cluster = ItemEmbedding[None, ClusterMetadata](
                cluster.prototype_id,
                cluster.embedding,
                metadata={**cluster.metadata.model_dump()} 
            )
            if cluster.prototype_id in label_results:
                result = label_results[cluster.prototype_id]
                if (not isinstance(result, Exception) and result.confidence >= label_confidence_threshold):                    
                    updated_cluster.metadata['label'] = result.label
                updates.append(updated_cluster)
            else:
                updates.append(updated_cluster)

        if merges:
            self.cluster_embedding_store.delete(list(merged_ids))

        self.cluster_embedding_store.upsert(updates)


    def update_cluster_label(self, cluster_id: str, label: str) -> bool:
        """
        Update the embedding store with clusters, applying merges if provided.
        Old clusters that have been merged are removed from the store.
        """
        result = self.get_clusters(cluster_id=cluster_id, include=['metadatas'])
        if(len(result)) == 0: return False
        updated_meta=result[cluster_id].metadata
        updated_meta.label = label
        updated_cluster = ItemEmbeddingUpdate(item_id=cluster_id, metadata=updated_meta.model_dump())
        self.cluster_embedding_store.update([updated_cluster])
        return True


    # TODO: accept prompt_ids that are lablled and fetch label from meta
    #args: ids and label
    def calculate_cluster_accuracy(self) -> ClusterAccuracy:
        true_labels: dict[ItemId, str] = {}
        assignments: Assignments = {}
        for p in  self.stream_all_prompts():
            ## temp solution
            assignments[p.prompt_id] = p.metadata.cluster_id
            label = p.prompt_id.split("_")[0]
            if not label: 
                print(f"[WARNING] {p.prompt_id} is not a valid labelled item.")
                continue
            true_labels[p.prompt_id] = label
        return calculate_cluster_accuracy(true_labels, assignments)
    
    def calculate_prompt_cost(self, prompt_content, price_per_1m_tokens: float, model:  TextEmbeddingModel) -> float:
        return embedding_token_cost(prompt_content, price_per_1m_tokens, model)

    def get_all_prompt_embeddings(self) -> tuple[List[ItemId], List[ndarray], List[ClusterId]]:
        ids, embeddings, cluster_ids = [], [], []
        for id_, emb, cluster_id in self.stream_all_prompt_embeddings():
            ids.append(id_)
            embeddings.append(emb)
            cluster_ids.append(cluster_id)
        return ids, embeddings, cluster_ids
    
    def stream_all_prompt_embeddings(self, batch_size: Optional[int] = None) -> Iterable[tuple[ItemId, ndarray, ClusterId]]:
        count = self.prompt_embedding_store.count()
        for batch in paginated_read(
            lambda offset, limit: self.prompt_embedding_store.get(
                include=["embeddings", "metadatas"],
                offset=offset,
                limit=limit,
            ),
            total=count,
            limit=batch_size or 500,
            ):
            yield from zip(batch.ids, batch.embeddings, [m.get("cluster_id") for m in batch.metadatas])

    def get_all_prompts(self, ids: Optional[List[str]], cluster_id: Optional[ClusterId] = None, batch_size: Optional[int] = None) -> Iterable[Prompt]:
        return list(self.stream_all_prompts(ids, cluster_id, batch_size))
    
    def get_prompts_paginate(self, ids: Optional[List[str]] = None, cluster_id: Optional[ClusterId] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Prompt]:
        result = self.prompt_embedding_store.get(
                ids = ids,
                filter={"cluster_id": cluster_id} if cluster_id else None,
                include=["metadatas", "documents"],
                offset=offset,
                limit=limit,
            )
        return self._to_prompts(result)

    def query_prompts(self, text_embedder: TextEmbeddingProvider, query: str, cluster_id: Optional[ClusterId] = None, limit: Optional[int] = None) -> List[Prompt]:
        embed = text_embedder.embed(query)
        limit = limit or 10
        result = self.prompt_embedding_store.query(query_embeds=[embed], limit=limit, filter={"cluster_id": cluster_id} if cluster_id else None, include=["metadatas", "documents"])
        return self._to_prompts(result)
    
    def stream_all_prompts(self, ids: Optional[List[str]] = None, cluster_id: Optional[ClusterId] = None, limit: Optional[int] = None) -> Iterable[Prompt]:
        limit = limit or 100
        for batch in paginated_read_until_empty(
            lambda offset, limit: self.prompt_embedding_store.get(
                ids = ids,
                filter={"cluster_id": cluster_id} if cluster_id else None,
                include=["metadatas", "documents"],
                offset=offset,
                limit=limit,
            ),
            break_fn= lambda batch: len(batch.metadatas) == 0,
            limit=limit,
            ):
            yield from self._to_prompts(batch)
            
    def get_prompts_metadata(self, ids: list[str]) -> list[PromptMetadata]:
        return list(self.stream_prompts_metadata(ids))
    

    def stream_prompts_metadata(self, ids: list[str]) -> Iterable[PromptMetadata]:
        for batch in paginated_read(
            lambda offset, limit: self.prompt_embedding_store.get(
                ids = ids,
                include=["metadatas"],
                offset=offset,
                limit=limit,
            ),
            total=len(ids),
            limit=500,
            ):
            yield from [ PromptMetadata(**m) for m in batch.metadatas]   

    def get_prompts_overview(self) -> PromptsOverviewInfo:
        prompt_count = self.prompt_embedding_store.count()
        cluster_count = self.cluster_embedding_store.count()
        average_prompt_cost = 0 #TODO calculate avg prompt cost
        return PromptsOverviewInfo(total_prompts=prompt_count, total_clusters=cluster_count, average_prompt_cost=average_prompt_cost)

    def get_existing_labels(self) -> list[str]:
        labels: list[str] = []
        for batch in paginated_read_until_empty(
            fetch_fn=lambda offset, limit: self.cluster_embedding_store.get(
                include=['metadatas'], filter={"label": {"$ne": Cluster.UNLABELLED}},
                limit=limit,
                offset=offset
                ),
            break_fn=lambda batch: len(batch.metadatas) == 0,
            limit=500,
            ):
            labels.extend([m.get("label") for m in batch.metadatas])
        return labels
    

    def get_clusters(self, cluster_id: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None, include: Include = ['metadatas', 'embeddings']) -> dict[ClusterId, Cluster | ClusterNoEmbeddings]:
        clusters: Dict[ClusterId, Cluster] = {}
        results = self.cluster_embedding_store.get(
                ids = [cluster_id] if cluster_id else None,
                include=include,
                limit=limit,
                offset=offset
                )
        if "embeddings" in include:
            for cluster_id, embedding, metadata in zip(results.ids, results.embeddings, results.metadatas):
                clusters[cluster_id] = Cluster(cluster_id, embedding, ClusterMetadata(**metadata), label=metadata.get("label"))
        else:
            for cluster_id, metadata in zip(results.ids, results.metadatas):
                clusters[cluster_id] = ClusterNoEmbeddings(prototype_id=cluster_id, metadata=ClusterMetadata(**metadata), label=metadata.get("label"))
        return clusters
    
    def get_all_clusters(self) -> dict[ClusterId, Cluster]:
        clusters: Dict[ClusterId, Cluster] = {}
        for batch in paginated_read_until_empty(
            fetch_fn=lambda offset, limit: self.cluster_embedding_store.get(
                include=['metadatas', 'embeddings'],
                limit=limit,
                offset=offset
                ),
            break_fn=lambda batch: len(batch.metadatas) == 0,
            limit=500
            ):
            for cluster_id, embedding, metadata in zip(batch.ids, batch.embeddings, batch.metadatas):
                clusters[cluster_id] = Cluster(cluster_id, embedding, ClusterMetadata(**metadata), label=metadata.get("label"))
        return clusters
        
    def _get_labelling_prompt(self, cluster_id: str, existing_labels: list[str], sample_prompts: list[str]) -> str:
        return f"""## ClusterId: {cluster_id}\n\n##Existing labels {existing_labels} Cluster sample_prompts \n\n {sample_prompts}"""
    
    def _has_llm_client(self) -> bool:
        return self.llm != None
    
    def _to_prompts(self, result: GetResult | QueryResult) -> List[Prompt]:
        return [ Prompt(prompt_id=prompt_id, content=prompt_content,  metadata=PromptMetadata(**metadata)) for prompt_id, metadata, prompt_content in zip(result.ids, result.metadatas, result.datas) ]
    