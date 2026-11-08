from typing import Protocol

from sereleum.data.stores.store import Store
from sereleum.schemas.cluster import ClusterCrossRef

class ClusterCrossRefStore(Store[ClusterCrossRef], Protocol):
    
     async def move(
          self,
          destination_collection_id: str,
          source_collection_id: str,
          item_ids: list[str] | None,
          *,
          select_all: bool = False,
          excluded_item_ids: list[str] | None = None,
      ) -> None: ...