from abc import ABC
from typing import Generic

from sqlalchemy import Select, delete, select, exists

from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.schemas.tag import Tag
from sereleum.data.types import TPostgresTagCrossRefModel, TPostgresItemModel, TPostgresTagModel, Filter

class PostgresTagStore(
    Generic[TPostgresTagModel, TPostgresTagCrossRefModel, TPostgresItemModel],
    BasePostgresStore[TPostgresTagModel, Tag],
    ABC,
):
    item_model: type[TPostgresItemModel]
    crossref_model: type[TPostgresTagCrossRefModel]

    def apply_filters(
        self,
        stmt: Select,
        f: Filter | None,
    ) -> Select:
        if not f:
            return stmt
        
        if (ids := f.get('ids') )is not None:
            stmt = stmt.where(self.model.id.in_(ids))

        if (name := f.get('name')) is not None:
            stmt = stmt.where(self.model.name == name)

        return stmt


    async def delete_by_ids(self, ids: list[str]) -> None:
        if not ids:
            return

        async with self.sessionmaker() as session:
            stmt = delete(self.model).where(self.model.id.in_(ids))
            await session.execute(stmt)
            await session.commit()
