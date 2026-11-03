from abc import ABC, abstractmethod
from typing import Generic, Set, List, Optional

from sereleum.data.types import Filter, TCollection
from sereleum.collections.types import CollectionId

class CollectionManager(ABC, Generic[TCollection]):

    @abstractmethod
    async def move(self, item_ids: Set[str], destination_collection_id: CollectionId, source_collection_id: CollectionId) -> None: ...

    @abstractmethod
    async def merge(self, primary_collection_id: CollectionId, secondary_collection_ids: List[CollectionId]) -> None: ...

    @abstractmethod
    async def rename(self, collection_id: CollectionId, name: str) -> None: ...

    async def delete(self, collection_ids: List[CollectionId]) -> None:
        raise NotImplementedError()

    async def remove(self, collection_id: CollectionId, item_ids: Set[str]) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_collections(
        self,
        filter: Optional[Filter] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        ascending: bool = True
        ) -> List[TCollection]: ...