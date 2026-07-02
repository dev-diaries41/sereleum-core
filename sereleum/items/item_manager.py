import random
import math

from numpy import ndarray
from datetime import datetime
from typing import List, Optional, Tuple, Any, Generator, Dict, Generic

from smartscan import ItemEmbedding, ClusterMerges, ItemId, ItemEmbeddingUpdate, GetResult, QueryResult, ClusterResult
from smartscan.embeds import EmbeddingStore

from sereleum.schemas.items.item import TData, TItem, TMetadata
from sereleum.store.helpers import   paginate_until
from sereleum.errors import SereleumError, ErrorCode
from sereleum.constants import UNCLUSTERED

from abc import abstractmethod


class ItemManager(Generic[TItem, TData, TMetadata]):
    def __init__(self, 
        embedding_store: EmbeddingStore,
                 ): 
        self.embedding_store = embedding_store
        
    def reassign_item(self, item_id: str, new_cluster_id: str) -> None:
        items = self.get_by_ids([item_id])
        if len(items) == 0:
            raise SereleumError("Item not found", code=ErrorCode.ITEM_NOT_FOUND)
        item = items[0]
        updated_metadata = ItemEmbeddingUpdate(
                    item_id,
                    metadata=self._update_metadata(item.metadata.model_dump(), new_cluster_id),
                )
        self.embedding_store.update([updated_metadata]) 


    def assign(self, result: ClusterResult) -> None:
        if not result.assignments: return
        item_ids = [str(k) for k in result.assignments.keys()]
        updated_items: list[ItemEmbedding] = []

        for item_id, metadata in self.stream_metadata_by_ids(item_ids):
            original_cluster = result.assignments[item_id]

            new_cluster_id = next(
                (mid for mid, clusters in result.merges.items()
                if original_cluster in clusters),
                original_cluster,
            )

            updated_items.append(
                ItemEmbeddingUpdate(
                    item_id,
                    metadata=self._update_metadata(metadata.model_dump(), new_cluster_id)
                )
            )
        self.embedding_store.update(updated_items)


    def reassign_from_merges(self, merges: ClusterMerges) -> None:
        all_target_cluster_ids = [cid for targets in merges.values() for cid in targets]
        updated_items: list[ItemEmbedding] = []

        for item_id, metadata in self.stream_metadata(cluster_ids=all_target_cluster_ids):
            original_cluster = metadata.cluster_id
            new_cluster_id = next(
                (mid for mid, clusters in merges.items()
                if original_cluster in clusters),
                original_cluster,
            )

            updated_items.append(
                ItemEmbeddingUpdate(
                    item_id,
                    metadata=self._update_metadata(metadata, new_cluster_id),
                )
            )
        self.embedding_store.update(updated_items)

    # Prevents large number of reads whilst maximising data coverage
    def get_samples(self, sample_size: int, cluster_ids: Optional[List[str]] = None, batch_size: int= 100, exclude_clustered: bool = False) -> Tuple[List[ItemId], List[TMetadata], List[ndarray]]:
        id_list, metadata_list, embedding_list = [], [], []
        total_items = self.embedding_store.count()
        max_sample_size = sample_size if total_items >= sample_size else total_items

        for id_, metadata, emb in self.stream_metadata(cluster_ids=cluster_ids, batch_size=batch_size, with_embeddings=True, exclude_clustered=exclude_clustered):
            if len(id_list) < max_sample_size:
                id_list.append(id_)
                metadata_list.append(metadata)
                embedding_list.append(emb)
            else:
                scale = max_sample_size / total_items # ensure step size is scaled to sample size
                n_sections = 5
                step_size =  total_items // n_sections
                scaled_step_size =  math.floor(scale * step_size)
                initial_offset = step_size
                
                while initial_offset < total_items:
                    for idx, (id_, metadata, emb) in enumerate(self.stream_metadata(cluster_ids=cluster_ids, batch_size=batch_size, initial_offset=initial_offset, with_embeddings=True)):
                        if idx >= scaled_step_size: # prevents excessive reads!!
                            break
                        # randomly keep or replace with a unique item
                        if random.random() > 0.5:
                            id_list[idx] = id_
                            metadata_list[idx] = metadata
                            embedding_list[idx] = emb
                    initial_offset += step_size # increase in real step size to enusre the entire db is passed in n_sections
        return id_list, metadata_list, embedding_list
    

    def get(self, ids: Optional[List[str]] = None, cluster_ids: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None, exclude_clustered: bool = False) -> List[TItem]:
        if ids: return self.get_by_ids(ids)
        
        cluster_filter = self._get_cluster_filter(cluster_ids, exclude_clustered)
        result = self.embedding_store.get(
                filter=cluster_filter,
                include=["metadatas", "documents"],
                offset=offset,
                limit=limit,
            )
        return self.to_items(result)

    def query(self, embed: ndarray, cluster_ids: Optional[List[str]] = None, limit: int = 10) -> List[TItem]:
        limit = limit
        result = self.embedding_store.query(
            query_embeds=[embed], 
            limit=limit, 
                filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None,
            include=["metadatas", "documents"]
            )
        return self.to_items(result)
    
    def get_by_ids(self, ids: List[str], batch_size: int= 100) -> List[TItem]:
        return list(self.stream_by_ids(ids, batch_size))
    
    # This handle cases where the number of ids may be very high
    def stream_by_ids(self, ids: List[str], batch_size: int= 100, exclude_clustered: bool = False) -> Generator[TItem, Any, None]:
        cluster_filter = self._get_cluster_filter(None, exclude_clustered)
        start = 0

        while start < len(ids):
            result = self.embedding_store.get(
                filter=cluster_filter,
                ids = ids[start:start + batch_size],
                include=["metadatas", "documents"],
            )
            if len(result.metadatas) == 0:
                break
            yield from self.to_items(result)
            start += batch_size
    
    def stream(self, cluster_ids: Optional[List[str]] = None, batch_size: int= 100, initial_offset: int = 0, exclude_clustered: bool = False) -> Generator[TItem, Any, None]:
        cluster_filter = self._get_cluster_filter(cluster_ids, exclude_clustered)
        for batch in paginate_until(
            lambda offset, batch_size: self.embedding_store.get(
                filter=cluster_filter,
                include=["metadatas", "documents"],
                offset=offset,
                limit=batch_size,
            ),
            break_fn= lambda batch: len(batch.metadatas) == 0,
            batch_size=batch_size,
            initial_offset = initial_offset
            ):
            yield from self.to_items(batch)
            
    
    # Note: tokens in metadata shouldnt be none here
    def stream_metadata_by_ids(self, ids: list[str], batch_size: int= 100, with_embeddings: bool = False, exclude_clustered: bool = False) -> Generator[tuple[str, TMetadata] | tuple[str, TMetadata, ndarray], Any, None]:
        cluster_filter = self._get_cluster_filter(None, exclude_clustered)

        start = 0

        while start < len(ids):
            result = self.embedding_store.get(
                filter=cluster_filter,
                ids=ids[start:start + batch_size],
                include=["metadatas"],
            )
            if len(result.metadatas) == 0:
                break
            yield from self.to_item_tuples(result, with_embeddings=with_embeddings)
            start += batch_size

    
    # Note: tokens in metadata shouldnt be none here
    def stream_metadata(self, cluster_ids: Optional[List[str]] = None, batch_size: int= 100, initial_offset: int = 0,  with_embeddings: bool = False, exclude_clustered: bool = False) -> Generator[tuple[str, TMetadata] | tuple[str, TMetadata, ndarray], Any, None]:
        cluster_filter = self._get_cluster_filter(cluster_ids, exclude_clustered)
        for batch in paginate_until(
            lambda offset, limit: self.embedding_store.get(
                filter=cluster_filter,
                include=["metadatas", "embeddings"] if with_embeddings else ["metadatas"],
                offset=offset,
                limit=limit,
            ),
            break_fn= lambda batch: len(batch.metadatas) == 0,
            batch_size=batch_size,
            initial_offset = initial_offset   
                              ):
            yield from self.to_item_tuples(batch, with_embeddings=with_embeddings)
   
   
    @staticmethod
    def _update_metadata(old_meta: dict, new_cluster_id: str) -> Dict:
        updated_at = datetime.now().isoformat()
        old_meta['cluster_id'] = new_cluster_id
        old_meta['updated_at'] = updated_at
        return old_meta


    @abstractmethod
    def to_items(self, result: GetResult | QueryResult) -> List[TItem]:
        raise NotImplementedError

    @abstractmethod
    def to_item_tuples(self, result: GetResult | QueryResult, with_embeddings: bool = False)  -> tuple[str, TMetadata] | tuple[str, TMetadata, ndarray]:
        raise NotImplementedError
    
    def _get_cluster_filter(self, cluster_ids: Optional[List[str]], exclude_clustered: bool):
        cluster_filter={"cluster_id": {"$in": cluster_ids}} if cluster_ids else None
        if exclude_clustered and not cluster_filter:
            cluster_filter = {"cluster_id": {"$eq": UNCLUSTERED}}
        return cluster_filter
