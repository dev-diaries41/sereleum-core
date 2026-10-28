from typing import Protocol, TypeVar

from sereleum.data.stores.store import Store
from sereleum.schemas.cluster import StoredClusterMetadata

TCluster = TypeVar("TCluster")

class ClusterStore(Store[TCluster, StoredClusterMetadata], Protocol):
    async def delete_by_ids(self, ids: list[str]) -> None: ...
    async def get_unclustered_item_ids(self) -> list[str]: ...