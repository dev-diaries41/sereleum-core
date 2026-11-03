from typing import Protocol

from sereleum.data.stores.store import Store
from sereleum.schemas.tag import Tag

class TagStore(Store[Tag], Protocol):
    async def delete_by_ids(self, ids: list[str]) -> None: ...
