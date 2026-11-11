from typing import Protocol

from sereleum.data.stores.store import Store
from sereleum.data.types import TItem, Filter

class ItemStore(Store[TItem], Protocol):
    async def check_unindexed_items(self, ids: list[str]) -> list[str]: ...
    async def get_ids(
            self,
            filter: Filter | None = None,
            limit: int | None = None,
        ) -> list[str]: ...