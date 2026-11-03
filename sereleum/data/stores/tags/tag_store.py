from typing import Protocol, Optional

from sereleum.data.stores.store import Store
from sereleum.schemas.tag import Tag
from sereleum.data.types import Filter
from sereleum.schemas.collection import BaseCollection

class TagStore(Store[Tag], Protocol):
    async def delete_by_ids(self, ids: list[str]) -> None: ...
    async def get_collections(
        self,  
        filter: Optional[Filter] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        ascending: bool = True
    ) -> list[BaseCollection]: 
        ...
    async def merge(self, primary_tag_id: int, secondary_tag_ids: list[int]) -> None: ...
    async def tag(self, tag_name: str, item_ids: list[int]): ...
