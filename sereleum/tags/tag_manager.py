
from typing import Generic

from sereleum.collections.types import CollectionId
from sereleum.errors import SereleumError, ErrorCode
from sereleum.schemas.tag import TagCrossRef
from sereleum.collections.collecion_manager import CollectionManager
from sereleum.data.stores.tags.tag_crossref_store import TagCrossRefStore
from sereleum.data.stores.tags.tag_store import TagStore
from sereleum.data.types import TCollection

class TagManager(Generic[TCollection], CollectionManager[TCollection]):
    def __init__(
        self, 
        tag_store: TagStore,
        crossrefs_store: TagCrossRefStore,
        ): 
        self.tag_store = tag_store
        self.crossrefs_store = crossrefs_store 

    async def tag(
            self,
            tag_name: str,
            collection_id: CollectionId,
            item_ids: list[str] | None = None,
            *,
            select_all: bool = False,
            excluded_item_ids: list[str] | None = None,
        ) -> None:
        await self.tag_store.tag(tag_name, collection_id, item_ids, select_all=select_all, excluded_item_ids=excluded_item_ids)



    async def rename(self, collection_id: int, name) -> None:
        result = await self.tag_store.get(filter={'ids': [collection_id]})
        if(len(result)) == 0:
            raise SereleumError( "Cluster not found", code=ErrorCode.CLUSTER_NOT_FOUND)
        metadata=result[0]
        metadata.label = name
        await self.tag_store.update([metadata])

    async def get_collections(
        self,
        filter = None,
        limit = None,
        offset = 0,
        order_by = None,
        ascending = False
    ) -> list[TCollection]:
       return await self.tag_store.get_collections(
            filter=filter,
            limit=limit,
            offset=offset,
            order_by=order_by,
            ascending=ascending
            )


    async def merge(self, primary_collection_id: int, secondary_collection_ids: list[int]):
        await self.tag_store.merge(primary_collection_id, secondary_collection_ids)
    
    async def delete(self, collection_ids: list[int]):
        return await self.tag_store.delete_by_ids(collection_ids)

    # TODO; change to delete_by_ids
    async def remove(self, collection_id: int, item_ids):
        await self.crossrefs_store.delete([TagCrossRef(item_id=item_id, tag_id=collection_id) for item_id in item_ids])