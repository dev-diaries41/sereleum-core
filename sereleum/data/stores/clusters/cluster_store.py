from typing import Protocol

from sereleum.data.stores.store import Store
from sereleum.schemas.cluster import StoredClusterMetadata
from sereleum.schemas.collection import BaseCollection
from sereleum.data.types import Filter

class ClusterStore(Store[StoredClusterMetadata], Protocol):
    async def delete_by_ids(self, ids: list[str]) -> None: ...
    async def get_unclustered_item_ids(self) -> list[str]: ...
    async def get_collections(self, filter: Filter | None) -> list[BaseCollection]: ...