from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Set, List

from sereleum.collections.types import CollectionId


Collection = TypeVar("Collection")

class CollectionManager(ABC, Generic[Collection]):

    @abstractmethod
    async def move(self, item_ids: Set[str], new_collection_id: CollectionId, current_collection_id: CollectionId) -> None: ...

    @abstractmethod
    async def merge(self, primary_collection_id: CollectionId, secondary_collection_ids: List[CollectionId]) -> None: ...

    @abstractmethod
    async def rename(self, collection_id: CollectionId, name: str) -> None: ...

    async def delete(self, collection_ids: List[CollectionId]) -> None:
        raise NotImplementedError()

    async def remove(self, collection_id: CollectionId, item_ids: Set[str]) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_collections(self) -> List[Collection]: ...