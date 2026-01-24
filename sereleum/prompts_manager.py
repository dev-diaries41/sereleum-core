import asyncio 
import random

import numpy as np
from numpy import ndarray
from datetime import datetime
from typing import List, Dict, Optional, Iterable, Tuple

from smartscan import ItemEmbedding, Cluster, ClusterNoEmbeddings, ClusterMetadata, Assignments, ClusterMerges, ItemId, TextEmbeddingProvider, ClusterId, ClusterAccuracy, ItemEmbeddingUpdate, Include, GetResult, QueryResult
from smartscan.classify import  calculate_cluster_accuracy
from smartscan.embeds import EmbeddingStore, generate_prototype_embedding

from sereleum.types import Prompt, PromptMetadata, PromptsOverviewInfo
from sereleum.schemas.llm import LLMClassificationResult
from sereleum.providers.llm.llm_client import LLMClient
from sereleum.utils import  paginated_read, paginated_read_until_empty
from sereleum.errors import ReveliumError, ErrorCode


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
                

    def update_prompt_cluster(self, prompt_id: str, new_cluster_id: str) -> None:
        updated_at = datetime.now().isoformat()
        prompts = self.get_prompts_by_id([prompt_id])
        if len(prompts) == 0:
            raise ReveliumError("Prompt not found", code=ErrorCode.PROMPT_NOT_FOUND)
        prompt = prompts[0]
        updated_metadata = ItemEmbeddingUpdate(
                    prompt_id,
                    metadata=PromptMetadata(cluster_id=new_cluster_id, created_at=prompt.metadata.created_at, updated_at=updated_at, tokens=prompt.metadata.tokens).model_dump()
                )
        self.prompt_embedding_store.update([updated_metadata]) 


    def update_prompts_from_assignments(self, assignments: Assignments, merges: ClusterMerges) -> None:
        prompt_ids = [str(k) for k in assignments.keys()]
        updated_at = datetime.now().isoformat()
        updated_prompts: list[ItemEmbedding] = []

        for prompt_id, metadata in self.stream_prompts_metadata_by_ids(prompt_ids):
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
                    metadata=PromptMetadata(cluster_id=new_cluster, created_at=metadata.created_at, updated_at=updated_at, tokens=metadata.tokens).model_dump()
                )
            )
        self.prompt_embedding_store.update(updated_prompts)


    def update_prompts(self, merges: ClusterMerges) -> None:
        all_target_cluster_ids = [cid for targets in merges.values() for cid in targets]
        updated_at = datetime.now().isoformat()
        updated_prompts: list[ItemEmbedding] = []

        for prompt_id, metadata in self.stream_prompts_metadata(cluster_ids=all_target_cluster_ids):
            original_cluster = metadata.cluster_id
            new_cluster = next(
                (mid for mid, clusters in merges.items()
                if original_cluster in clusters),
                original_cluster,
            )

            updated_prompts.append(
                ItemEmbeddingUpdate(
                    prompt_id,
                    metadata=PromptMetadata(
                        cluster_id=new_cluster,
                        created_at=metadata.created_at,
                        updated_at=updated_at,
                        tokens=metadata.tokens,
                    ).model_dump(),
                )
            )
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

        # label_tasks = {
        #     cluster_id: async_label_prompts(cluster_id)
        #     for cluster_id, cluster in effective_clusters.items()
        #     if cluster.label == Cluster.UNLABELLED
        # }
        label_results = {}
        # if label_tasks:
        #     results = await asyncio.gather(*label_tasks.values(), return_exceptions=True)
        #     label_results = dict(zip(label_tasks.keys(), results))

        updated_clusters: list[ItemEmbedding[None, ClusterMetadata]] = []
        
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
                updated_clusters.append(updated_cluster)
            else:
                updated_clusters.append(updated_cluster)

        if merges:
            self.cluster_embedding_store.delete(list(merged_ids))

        self.cluster_embedding_store.upsert(updated_clusters)

    
    def merge_clusters(self, merges: ClusterMerges) -> List[ClusterNoEmbeddings]:
        self.update_prompts(merges)
        merged_clustered_ids = {cid for targets in merges.values() for cid in targets}
        all_clusters = self.get_all_clusters()

       # MUST happen after get all clusters!!!
        self.cluster_embedding_store.delete(list(merged_clustered_ids)) 

        updated_clusters: List[ItemEmbedding[None, ClusterMetadata]] = []

        for merge_id in merges.keys():
            cluster = self.get_clusters(cluster_ids=[merge_id], include=['metadatas'])[merge_id]
            _, embeds, _  = self.get_prompt_sample_embeddings(1e5, cluster_ids=[merge_id])
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
        self.cluster_embedding_store.upsert(updated_clusters)

        return [ClusterNoEmbeddings(prototype_id=c.item_id, metadata=c.metadata, label=c.metadata['label']) for c in updated_clusters]


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
        self.cluster_embedding_store.update([updated_cluster])
        return True


    # TODO: accept prompt_ids that are lablled and fetch label from meta
    #args: ids and label
    def calculate_cluster_accuracy(self) -> ClusterAccuracy:
        true_labels: dict[ItemId, str] = {}
        assignments: Assignments = {}
        for p in  self.stream_prompts():
            ## temp solution
            assignments[p.prompt_id] = p.metadata.cluster_id
            label = p.prompt_id.split("_")[0]
            if not label: 
                print(f"[WARNING] {p.prompt_id} is not a valid labelled item.")
                continue
            true_labels[p.prompt_id] = label
        return calculate_cluster_accuracy(true_labels, assignments)
    

    def get_prompt_sample_embeddings(self, sample_size: int, cluster_ids: Optional[List[str]] = None, batch_size: Optional[int] = None,) -> Tuple[List[ItemId], List[ndarray], List[ClusterId]]:
        ids, embeddings, cluster_ids = [], [], []
        for id_, emb, _cluster_id in self.stream_prompt_embeddings(cluster_ids=cluster_ids, batch_size=batch_size):
            if len(ids) >= sample_size:
                break
            ids.append(id_)
            embeddings.append(emb)
            cluster_ids.append(_cluster_id)
        return ids, embeddings, cluster_ids
    
    def stream_prompt_embeddings(self, cluster_ids: Optional[List[str]] = None, batch_size: Optional[int] = None) -> Iterable[Tuple[ItemId, ndarray, ClusterId]]:
        for batch in paginated_read_until_empty(
            lambda offset, limit: self.prompt_embedding_store.get(
                include=["embeddings", "metadatas"],
                filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None,
                offset=offset,
                limit=limit,
            ),
            break_fn= lambda batch: len(batch.embeddings) == 0,
            limit=batch_size or 500,
            ):
            yield from zip(batch.ids, batch.embeddings, [m.get("cluster_id") for m in batch.metadatas])


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
    
    # This handle cases where the number of ids may be very high
    def get_prompts_by_id(self, ids: List[str], batch_size: Optional[int] = None) -> List[Prompt]:
        batch_size = batch_size or 100
        start = 0
        prompts = []

        while start < len(ids):
            result = self.prompt_embedding_store.get(
                ids = ids[start:start + batch_size],
                include=["metadatas", "documents"],
            )
            if len(result.metadatas) == 0:
                break
            prompts.extend(self._to_prompts(result))
            start += batch_size
        return prompts
    
    def stream_prompts(self, cluster_id: Optional[ClusterId] = None, limit: Optional[int] = None) -> Iterable[Prompt]:
        limit = limit or 100
        for batch in paginated_read_until_empty(
            lambda offset, limit: self.prompt_embedding_store.get(
                filter={"cluster_id": cluster_id} if cluster_id else None,
                include=["metadatas", "documents"],
                offset=offset,
                limit=limit,
            ),
            break_fn= lambda batch: len(batch.metadatas) == 0,
            limit=limit,
            ):
            yield from self._to_prompts(batch)
            
    
    # Note: tokens in metadata shouldnt be none here
    def stream_prompts_metadata_by_ids(self, ids: list[str], batch_size: int | None = None) -> Iterable[Tuple[str, PromptMetadata]]:
        batch_size = batch_size or 100
        start = 0

        while start < len(ids):
            result = self.prompt_embedding_store.get(
                ids=ids[start:start + batch_size],
                include=["metadatas"],
            )
            if len(result.metadatas) == 0:
                break
            for prompt_id, metadata in zip(ids[start:start + batch_size], result.metadatas):
                yield prompt_id, PromptMetadata(**metadata)
            start += batch_size

    
    # Note: tokens in metadata shouldnt be none here
    def stream_prompts_metadata(self, cluster_ids: Optional[List[str]] = None, batch_size: Optional[int] = None) -> Iterable[Tuple[str, PromptMetadata]]:
        batch_size = batch_size or 100
        for batch in paginated_read_until_empty(
            lambda offset, limit: self.prompt_embedding_store.get(
                filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None,
                include=["metadatas"],
                offset=offset,
                limit=limit,
            ),
            break_fn= lambda batch: len(batch.metadatas) == 0,
            limit=batch_size,
            ):
            for prompt_id, metadata in zip(batch.ids, batch.metadatas):
                yield prompt_id, PromptMetadata(**metadata)    

    def get_prompts_overview(self) -> PromptsOverviewInfo:
        prompt_count = self.prompt_embedding_store.count()
        cluster_count = self.cluster_embedding_store.count()
        top_clusters = self.get_top_clusters(5)
        token_counts: dict[ClusterId, int] = {}
        for cluster_id in top_clusters.keys():
            avg_tokens = self.calculate_avg_tokens_for_cluster(cluster_id, 1000)
            token_counts[cluster_id] = avg_tokens
        return PromptsOverviewInfo(total_prompts=prompt_count, total_clusters=cluster_count, top_cluster_token_counts=token_counts, top_clusters=top_clusters.values())

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
    

    def get_clusters(self, cluster_ids: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None, include: Include = ['metadatas', 'embeddings']) -> dict[ClusterId, Cluster | ClusterNoEmbeddings]:
        clusters: Dict[ClusterId, Cluster] = {}
        results = self.cluster_embedding_store.get(
                ids = cluster_ids if cluster_ids else None,
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
    
    def get_top_clusters(self, n: int) -> Dict[ClusterId, ClusterNoEmbeddings]:
        top_clusters: Dict[ClusterId, ClusterNoEmbeddings] = {}

        while True:
            max_prototype_size = max(
                (cluster.metadata.prototype_size for cluster in top_clusters.values()),
                default=0,
            )

            result = self.cluster_embedding_store.get(
                include=["metadatas"],
                limit=n,
                filter={"prototype_size": {"$gt": max_prototype_size + 1}},
            )

            if len(result.metadatas) == 0:
                break

            if len(result.metadatas) == n:
                top_clusters = {
                    cluster_id: ClusterNoEmbeddings(prototype_id=cluster_id, metadata=ClusterMetadata(**metadata), label = metadata.get("label")) 
                    for cluster_id, metadata in zip(result.ids, result.metadatas)
                }
            else:
                for cluster_id, metadata in zip(result.ids, result.metadatas):
                    top_clusters[cluster_id] = ClusterNoEmbeddings(prototype_id=cluster_id, metadata=ClusterMetadata(**metadata), label = metadata.get("label")) 

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

        for _, metadata in self.stream_prompts_metadata([cluster_id]):
            if prompts_count >= sample_size:
                break
            total_tokens += (metadata.tokens or 0)
            prompts_count += (1 if metadata.tokens else 0)
        return int(total_tokens / max(1, prompts_count))
            
    def _get_labelling_prompt(self, cluster_id: str, existing_labels: list[str], sample_prompts: list[str]) -> str:
        return f"""## ClusterId: {cluster_id}\n\n##Existing labels {existing_labels} Cluster sample_prompts \n\n {sample_prompts}"""
    
    def _has_llm_client(self) -> bool:
        return self.llm != None
    
    def _to_prompts(self, result: GetResult | QueryResult) -> List[Prompt]:
        return [ Prompt(prompt_id=prompt_id, content=prompt_content,  metadata=PromptMetadata(**metadata)) for prompt_id, metadata, prompt_content in zip(result.ids, result.metadatas, result.datas) ]
    