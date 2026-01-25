import random
import math

from numpy import ndarray
from datetime import datetime
from typing import List, Optional, Iterable, Tuple

from smartscan import ItemEmbedding,Assignments, ClusterMerges, ItemId, TextEmbeddingProvider, ClusterId, ItemEmbeddingUpdate, GetResult, QueryResult
from smartscan.embeds import EmbeddingStore

from sereleum.types import Prompt, PromptMetadata
from sereleum.providers.llm.llm_client import LLMClient
from sereleum.utils import   paginate_until
from sereleum.errors import ReveliumError, ErrorCode


class PromptsManager():
    def __init__(self, 
        embedding_store: EmbeddingStore,
        llm_client: Optional[LLMClient] = None,
                 ): 
        self.llm = llm_client
        self.embedding_store = embedding_store
        

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
        self.embedding_store.update([updated_metadata]) 


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
        self.embedding_store.update(updated_prompts)


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
        self.embedding_store.update(updated_prompts)

    # Designed to limit reads whilst covering all "sections" of the db
    # This helps prevents large number of reads for large number of prompts
    def get_prompt_sample_embeddings(self, sample_size: int, cluster_ids: Optional[List[str]] = None, batch_size: Optional[int] = None,) -> Tuple[List[ItemId], List[ndarray], List[ClusterId]]:
        id_list, embedding_list, cluster_id_list = [], [], []
        total_prompts = self.embedding_store.count()
        sample_size = sample_size if total_prompts >= sample_size else total_prompts

        for id_, emb, _cluster_id in self.stream_prompt_embeddings(cluster_ids=cluster_ids, batch_size=batch_size):
            if len(id_list) < sample_size:
                id_list.append(id_)
                embedding_list.append(emb)
                cluster_id_list.append(_cluster_id)
            else:
                scale = sample_size / total_prompts # ensure step size is scaled to sample size
                n_sections = 5
                step_size =  total_prompts // n_sections
                scaled_step_size =  math.floor(scale * step_size)
                initial_offset = step_size
                
                while initial_offset < total_prompts:
                    for idx, (id_, emb, _cluster_id) in enumerate(self.stream_prompt_embeddings(cluster_ids=cluster_ids, batch_size=batch_size, initial_offset=initial_offset)):
                        if idx >= scaled_step_size: # prevents excessive reads!!
                            break
                        # randomly keep or replace with a unique item
                        if random.random() > 0.5:
                            id_list[idx] = id_
                            embedding_list[idx] = emb
                            cluster_id_list[idx] = _cluster_id
                    initial_offset += step_size # increase in real step size to enusre the entire db is passed in n_sections
        return id_list, embedding_list, cluster_id_list
    
    def stream_prompt_embeddings(self, cluster_ids: Optional[List[str]] = None, batch_size: Optional[int] = None, initial_offset: Optional[int] = None) -> Iterable[Tuple[ItemId, ndarray, ClusterId]]:
        batch_size = batch_size or 100
        initial_offset = initial_offset or 0

        for batch in paginate_until(
            lambda offset, limit: self.embedding_store.get(
                include=["embeddings", "metadatas"],
                filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None,
                offset=offset,
                limit=limit,
            ),
            break_fn= lambda batch: len(batch.embeddings) == 0,
            batch_size=batch_size,
            initial_offset = initial_offset
            ):
            yield from zip(batch.ids, batch.embeddings, [m.get("cluster_id") for m in batch.metadatas])


    def get_prompts(self, ids: Optional[List[str]] = None, cluster_id: Optional[ClusterId] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Prompt]:
        if ids:
            return self.get_prompts_by_id(ids, batch_size=limit)
        
        result = self.embedding_store.get(
                filter={"cluster_id": cluster_id} if cluster_id else None,
                include=["metadatas", "documents"],
                offset=offset,
                limit=limit,
            )
        return self._to_prompts(result)

    def query_prompts(self, text_embedder: TextEmbeddingProvider, query: str, cluster_ids: Optional[List[str]] = None, limit: Optional[int] = None) -> List[Prompt]:
        embed = text_embedder.embed(query)
        limit = limit or 10
        result = self.embedding_store.query(
            query_embeds=[embed], 
            limit=limit, 
                filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None,
            include=["metadatas", "documents"]
            )
        return self._to_prompts(result)
    
    # This handle cases where the number of ids may be very high
    def get_prompts_by_id(self, ids: List[str], batch_size: Optional[int] = None) -> List[Prompt]:
        batch_size = batch_size or 100
        start = 0
        prompts = []

        while start < len(ids):
            result = self.embedding_store.get(
                ids = ids[start:start + batch_size],
                include=["metadatas", "documents"],
            )
            if len(result.metadatas) == 0:
                break
            prompts.extend(self._to_prompts(result))
            start += batch_size
        return prompts
    
    def stream_prompts(self, cluster_ids: Optional[List[str]] = None, batch_size: Optional[int] = None, initial_offset: Optional[int] = None) -> Iterable[Prompt]:
        batch_size = batch_size or 100
        initial_offset = initial_offset or 0

        for batch in paginate_until(
            lambda offset, batch_size: self.embedding_store.get(
                filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None,
                include=["metadatas", "documents"],
                offset=offset,
                limit=batch_size,
            ),
            break_fn= lambda batch: len(batch.metadatas) == 0,
            batch_size=batch_size,
            initial_offset = initial_offset
            ):
            yield from self._to_prompts(batch)
            
    
    # Note: tokens in metadata shouldnt be none here
    def stream_prompts_metadata_by_ids(self, ids: list[str], batch_size: Optional[int] = None) -> Iterable[Tuple[str, PromptMetadata]]:
        batch_size = batch_size or 100
        start = 0

        while start < len(ids):
            result = self.embedding_store.get(
                ids=ids[start:start + batch_size],
                include=["metadatas"],
            )
            if len(result.metadatas) == 0:
                break
            for prompt_id, metadata in zip(ids[start:start + batch_size], result.metadatas):
                yield prompt_id, PromptMetadata(**metadata)
            start += batch_size

    
    # Note: tokens in metadata shouldnt be none here
    def stream_prompts_metadata(self, cluster_ids: Optional[List[str]] = None, batch_size: Optional[int] = None, initial_offset: Optional[int] = None) -> Iterable[Tuple[str, PromptMetadata]]:
        batch_size = batch_size or 100
        initial_offset = initial_offset or 0

        for batch in paginate_until(
            lambda offset, limit: self.embedding_store.get(
                filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None,
                include=["metadatas"],
                offset=offset,
                limit=limit,
            ),
            break_fn= lambda batch: len(batch.metadatas) == 0,
            batch_size=batch_size,
            initial_offset = initial_offset   
                              ):
            for prompt_id, metadata in zip(batch.ids, batch.metadatas):
                yield prompt_id, PromptMetadata(**metadata)    

    def _to_prompts(self, result: GetResult | QueryResult) -> List[Prompt]:
        return [ Prompt(prompt_id=prompt_id, content=prompt_content,  metadata=PromptMetadata(**metadata)) for prompt_id, metadata, prompt_content in zip(result.ids, result.metadatas, result.datas) ]
    