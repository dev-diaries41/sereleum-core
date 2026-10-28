from typing import Protocol, TypeVar

from sereleum.data.stores.store import Store
from sereleum.schemas.cluster import StoredClusterMetadata
from sereleum.data.types import TEntity

class ClusterStore(Store[TEntity, StoredClusterMetadata], Protocol):
    async def delete_by_ids(self, ids: list[str]) -> None: ...
    async def get_unclustered_item_ids(self) -> list[str]: ...