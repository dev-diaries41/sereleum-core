from typing import List, Optional, Protocol

from sereleum.data.types import TDomain, Filter


class Store(Protocol[TDomain]):

    async def add(self, items: List[TDomain]) -> None: ...
    async def upsert(self, items: List[TDomain]) -> None: ...
    async def update(self, items: List[TDomain]) -> None: ...

    async def get(
        self,
        filter: Optional[Filter] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        ascending: bool = True,
    ) -> List[TDomain]: ...

    async def delete(self, items: List[TDomain]) -> None: ...
    async def count(self, filter: Optional[Filter] = None) -> int: ...