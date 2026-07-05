from abc import ABC, abstractmethod
from typing import Generic, List, Optional

from sqlalchemy import select, delete, func, Select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.dialects.postgresql import insert
from sereleum.data.types import TItemModel, TQueryFilter

class BaseStore(Generic[TItemModel, TQueryFilter], ABC):
    model: type[TItemModel]
    primary_key: str

    def __init__(
        self,
        sessionmaker: async_sessionmaker):
        self.sessionmaker =sessionmaker

    @abstractmethod
    def apply_filters(self, stmt: Select, filter: Optional[TQueryFilter]):
        """Modify SQLAlchemy statement with filters"""
        ...

    async def add(self, items: List[TItemModel]):
        if not items:
            return

        async with self.sessionmaker() as session:
            values = [
                {
                    column.name: getattr(item, column.name)
                    for column in self.model.__table__.columns
                }
                for item in items
            ]

            stmt = insert(self.model).values(values)
            stmt = stmt.on_conflict_do_nothing(index_elements=[self.primary_key])

            await session.execute(stmt)
            await session.commit()


    async def update(self, items: list[TItemModel]):
        if not items:
            return

        mappings = [
            {
                column.name: getattr(item, column.name)
                for column in self.model.__table__.columns
            }
            for item in items
        ]

        async with self.sessionmaker() as session:
            await session.run_sync(
                lambda sync_session: sync_session.bulk_update_mappings(
                    self.model,
                    mappings,
                )
            )
            await session.commit()

    async def get(
        self,
        filter: Optional[TQueryFilter] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        ascending: bool = True,
    ) -> List[TItemModel]:

        async with self.sessionmaker() as session:
            stmt = select(self.model)

            stmt = self.apply_filters(stmt, filter)

            if order_by is not None:
                col = getattr(self.model, order_by)
            else:
                col = getattr(self.model, self.primary_key)

            stmt = stmt.order_by(col.asc() if ascending else col.desc())

            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)
            else:
                stmt = stmt.offset(offset)

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_by_ids(self, ids: List[str]) -> List[TItemModel]:
        async with self.sessionmaker() as session:
            pk = getattr(self.model, self.primary_key)

            stmt = select(self.model).where(pk.in_(ids))
            result = await session.execute(stmt)

            return list(result.scalars().all())

    async def delete(self, ids: List[str]):
        if not ids:
            return

        async with self.sessionmaker() as session:
            pk = getattr(self.model, self.primary_key)

            stmt = delete(self.model).where(pk.in_(ids))
            await session.execute(stmt)
            await session.commit()

    async def count(self, filter: Optional[TQueryFilter] = None) -> int:
        async with self.sessionmaker() as session:
            stmt = select(func.count()).select_from(self.model)

            stmt = self.apply_filters(stmt, filter)

            result = await session.execute(stmt)
            return result.scalar_one()