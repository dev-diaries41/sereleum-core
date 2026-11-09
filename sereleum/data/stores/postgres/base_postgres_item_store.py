from abc import ABC
from typing import Generic

from sqlalchemy import select

from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.data.types import TPostgresItemModel, TItem


class PostgresItemStore(
    Generic[TPostgresItemModel, TItem],
    BasePostgresStore[TPostgresItemModel, TItem],
    ABC,
):
    async def check_unindexed_items(self, ids: list[str]) -> list[str]:
        if not ids:
            return []

        async with self.sessionmaker() as session:
            stmt = select(self.model.id).where(self.model.id.in_(ids))
            result = await session.execute(stmt)
            existing_ids = set(result.scalars().all())

        return [item_id for item_id in ids if item_id not in existing_ids]