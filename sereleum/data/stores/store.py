from typing import Generic, List, Optional, Protocol, TypeVar

from pydantic import BaseModel

from sereleum.data.mappers.mapper import Mapper
from sereleum.data.types import TEntity, TDomain

TFilter = TypeVar("TFilter", bound=BaseModel)


class Store(Protocol[TEntity, TDomain]):
    mapper: Mapper[TEntity, TDomain]

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