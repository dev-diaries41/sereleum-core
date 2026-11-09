from typing import Protocol, Optional

from sereleum.data.stores.store import Store
from sereleum.schemas.cluster import StoredClusterMetadata
from sereleum.schemas.collection import BaseCollection
from sereleum.data.types import Filter

class ClusterStore(Store[StoredClusterMetadata], Protocol):
    async def delete_by_ids(self, ids: list[str]) -> None: ...
    async def get_unclustered_item_ids(self) -> list[str]: ...
    async def get_collections(
        self,  
        filter: Optional[Filter] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        ascending: bool = True
    ) -> list[BaseCollection]: 
        ...
    async def update_labels(self, labelled_clusters: dict[str, str]) -> None: ...
