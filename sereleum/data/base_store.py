from abc import ABC, abstractmethod
from typing import Generic, List, Optional

from sqlalchemy import Select, func, inspect, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from sereleum.data.types import TItemModel
from pydantic import BaseModel


class BaseStore(Generic[TItemModel], ABC):
    model: type[TItemModel]

    def __init__(self, sessionmaker: async_sessionmaker):
        self.sessionmaker = sessionmaker

    @property
    def primary_keys(self):
        return inspect(self.model).primary_key

    @abstractmethod
    def apply_filters(self, stmt: Select, filter: Optional[BaseModel]):
        ...

    async def add(self, items: List[TItemModel]):
        if not items:
            return

        values = [
            {column.name: getattr(item, column.name) for column in self.model.__table__.columns}
            for item in items
        ]

        async with self.sessionmaker() as session:
            stmt = insert(self.model).values(values)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=[column.name for column in self.primary_keys]
            )
            await session.execute(stmt)
            await session.commit()

    async def update(self, items: List[TItemModel]):
        if not items:
            return

        mappings = [
            {column.name: getattr(item, column.name) for column in self.model.__table__.columns}
            for item in items
        ]

        async with self.sessionmaker() as session:
            await session.run_sync(
                lambda sync_session: sync_session.bulk_update_mappings(self.model, mappings)
            )
            await session.commit()

    async def get(
        self,
        filter: Optional[BaseModel] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        ascending: bool = True,
    ) -> List[TItemModel]:
        async with self.sessionmaker() as session:
            stmt = self.apply_filters(select(self.model), filter)
            column = getattr(self.model, order_by) if order_by else self.primary_keys[0]
            stmt = stmt.order_by(column.asc() if ascending else column.desc()).offset(offset)

            if limit is not None:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def delete(self, item: TItemModel):
        async with self.sessionmaker() as session:
            await session.delete(item)
            await session.commit()

    async def count(self, filter: Optional[BaseModel] = None) -> int:
        async with self.sessionmaker() as session:
            stmt = self.apply_filters(select(func.count()).select_from(self.model), filter)
            result = await session.execute(stmt)
            return result.scalar_one()
