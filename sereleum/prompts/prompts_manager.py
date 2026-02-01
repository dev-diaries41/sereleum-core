import random
import math

from numpy import ndarray
from datetime import datetime
from typing import List, Optional, Tuple, Any, Generator

from smartscan import ItemEmbedding,Assignments, ClusterMerges, ItemId, TextEmbeddingProvider, ClusterId, ItemEmbeddingUpdate, GetResult, QueryResult
from smartscan.embeds import EmbeddingStore

from sereleum.prompts.types import Prompt, PromptMetadata
from sereleum.utils.batch import   paginate_until
from sereleum.errors import ReveliumError, ErrorCode


class PromptsManager():
    def __init__(self, 
        embedding_store: EmbeddingStore,
                 ): 
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
    # This helps prevents large number of reads for large number of prompts or high meomry usage whehn plotting cluster plots
    def get_prompt_metadata_samples(self, sample_size: int, cluster_ids: Optional[List[str]] = None, batch_size: int= 100, exclude_clustered: bool = False) -> Tuple[List[ItemId], List[PromptMetadata], List[ndarray]]:
        id_list, metadata_list, embedding_list = [], [], []
        total_prompts = self.embedding_store.count()
        max_sample_size = sample_size if total_prompts >= sample_size else total_prompts

        for id_, metadata, emb in self.stream_prompts_metadata(cluster_ids=cluster_ids, batch_size=batch_size, with_embeddings=True, exclude_clustered=exclude_clustered):
            if len(id_list) < max_sample_size:
                id_list.append(id_)
                metadata_list.append(metadata)
                embedding_list.append(emb)
            else:
                scale = max_sample_size / total_prompts # ensure step size is scaled to sample size
                n_sections = 5
                step_size =  total_prompts // n_sections
                scaled_step_size =  math.floor(scale * step_size)
                initial_offset = step_size
                
                while initial_offset < total_prompts:
                    for idx, (id_, metadata, emb) in enumerate(self.stream_prompts_metadata(cluster_ids=cluster_ids, batch_size=batch_size, initial_offset=initial_offset, with_embeddings=True)):
                        if idx >= scaled_step_size: # prevents excessive reads!!
                            break
                        # randomly keep or replace with a unique item
                        if random.random() > 0.5:
                            id_list[idx] = id_
                            metadata_list[idx] = metadata
                            embedding_list[idx] = emb
                    initial_offset += step_size # increase in real step size to enusre the entire db is passed in n_sections
        return id_list, metadata_list, embedding_list
    

    def get_prompts(self, ids: Optional[List[str]] = None, cluster_ids: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Prompt]:
        if ids:
            return self.get_prompts_by_id(ids)
        
        result = self.embedding_store.get(
                filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None,
                include=["metadatas", "documents"],
                offset=offset,
                limit=limit,
            )
        return self._to_prompts(result)

    def query_prompts(self, text_embedder: TextEmbeddingProvider, query: str, cluster_ids: Optional[List[str]] = None, limit: int = 10) -> List[Prompt]:
        embed = text_embedder.embed(query)
        limit = limit
        result = self.embedding_store.query(
            query_embeds=[embed], 
            limit=limit, 
                filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None,
            include=["metadatas", "documents"]
            )
        return self._to_prompts(result)
    
    def get_prompts_by_id(self, ids: List[str], batch_size: int= 100) -> List[Prompt]:
        return list(self.stream_prompts_by_id(ids, batch_size))
    
    # This handle cases where the number of ids may be very high
    def stream_prompts_by_id(self, ids: List[str], batch_size: int= 100) -> Generator[Prompt, Any, None]:
        start = 0

        while start < len(ids):
            result = self.embedding_store.get(
                ids = ids[start:start + batch_size],
                include=["metadatas", "documents"],
            )
            if len(result.metadatas) == 0:
                break
            yield from self._to_prompts(result)
            start += batch_size
    
    def stream_prompts(self, cluster_ids: Optional[List[str]] = None, batch_size: int= 100, initial_offset: int = 0) -> Generator[Prompt, Any, None]:
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
    def stream_prompts_metadata_by_ids(self, ids: list[str], batch_size: int= 100, with_embeddings: bool = False) -> Generator[tuple[str, PromptMetadata] | tuple[str, PromptMetadata, ndarray], Any, None]:
        start = 0

        while start < len(ids):
            result = self.embedding_store.get(
                ids=ids[start:start + batch_size],
                include=["metadatas"],
            )
            if len(result.metadatas) == 0:
                break
            yield from self._to_prompt_metadata_tuples(result, with_embeddings=with_embeddings)
            start += batch_size

    
    # Note: tokens in metadata shouldnt be none here
    def stream_prompts_metadata(self, cluster_ids: Optional[List[str]] = None, batch_size: int= 100, initial_offset: int = 0,  with_embeddings: bool = False, exclude_clustered: bool = False) -> Generator[tuple[str, PromptMetadata] | tuple[str, PromptMetadata, ndarray], Any, None]:
        where={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None
        if exclude_clustered:
            where = {"cluster_id": {"$eq": PromptMetadata.UNCLUSTERED}}
            
        for batch in paginate_until(
            lambda offset, limit: self.embedding_store.get(
                filter=where,
                include=["metadatas", "embeddings"] if with_embeddings else ["metadatas"],
                offset=offset,
                limit=limit,
            ),
            break_fn= lambda batch: len(batch.metadatas) == 0,
            batch_size=batch_size,
            initial_offset = initial_offset   
                              ):
            yield from self._to_prompt_metadata_tuples(batch, with_embeddings=with_embeddings)


    def _to_prompts(self, result: GetResult | QueryResult) -> List[Prompt]:
        return [ Prompt(prompt_id=prompt_id, content=prompt_content,  metadata=PromptMetadata(**metadata)) for prompt_id, metadata, prompt_content in zip(result.ids, result.metadatas, result.datas) ]
    
    def _to_prompt_metadata_tuples(self, result: GetResult | QueryResult, with_embeddings: bool = False)  -> Generator[tuple[str, PromptMetadata] | tuple[str, PromptMetadata, ndarray], Any, None]:
        if not with_embeddings:
            return [ (prompt_id, PromptMetadata(**metadata)) for prompt_id, metadata in zip(result.ids, result.metadatas)]
        if len(result.embeddings) > 0 and with_embeddings:
            return [(prompt_id, PromptMetadata(**metadata), emb) for prompt_id, metadata, emb in zip(result.ids, result.metadatas, result.embeddings)]        
        else:
            raise ValueError("With embeddings is true but result has no embeddings")
        