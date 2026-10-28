from typing import List, Optional, Protocol

from pydantic import BaseModel

from sereleum.data.types import TDomain


class Store(Protocol[TDomain]):

    async def add(self, items: List[TDomain]) -> None: ...
    async def update(self, items: List[TDomain]) -> None: ...

    async def get(
        self,
        filter: Optional[BaseModel] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        ascending: bool = True,
    ) -> List[TDomain]: ...

    async def delete(self, items: List[TDomain]) -> None: ...
    async def count(self, filter: Optional[BaseModel] = None) -> int: ...