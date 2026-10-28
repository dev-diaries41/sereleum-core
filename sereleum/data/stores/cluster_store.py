from typing import Protocol

from sereleum.data.stores.store import Store
from sereleum.schemas.cluster import StoredClusterMetadata

class ClusterStore(Store[StoredClusterMetadata], Protocol):
    async def delete_by_ids(self, ids: list[str]) -> None: ...
    async def get_unclustered_item_ids(self) -> list[str]: ...