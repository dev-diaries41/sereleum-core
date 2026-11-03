from abc import ABC
from typing import Generic

from sqlalchemy import Select, delete, select, exists

from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.schemas.cluster import StoredClusterMetadata
from sereleum.data.types import TPostgresClusterModel, TPostgresItemModel, TPostgresClusterCrossRefModel, Filter

class PostgresClusterStore(
    Generic[TPostgresClusterModel, TPostgresClusterCrossRefModel, TPostgresItemModel],
    BasePostgresStore[TPostgresClusterModel, StoredClusterMetadata],
    ABC,
):
    item_model: type[TPostgresItemModel]
    crossref_model: type[TPostgresClusterCrossRefModel]


    def apply_filters(
        self,
        stmt: Select,
        f: Filter | None,
    ) -> Select:
        if not f:
            return stmt
        
        if (ids := f.get('ids') )is not None:
            stmt = stmt.where(self.model.id.in_(ids))

        if (label := f.get('label')) is not None:
            stmt = stmt.where(self.model.label == label)

        if (size:= f.get('size')) is not None:
            stmt = stmt.where( self.model.prototype_size == size )

        return stmt


    async def delete_by_ids(self, ids: list[str]) -> None:
        if not ids:
            return

        async with self.sessionmaker() as session:
            stmt = delete(self.model).where(self.model.id.in_(ids))
            await session.execute(stmt)
            await session.commit()


    async def get_unclustered_item_ids(self) -> list[str]:
        # All item models expose an id column, referenced by the cross-reference model's item_id.
        async with self.sessionmaker() as session:
            stmt = select(self.item_model.id).where(
                ~exists(
                    select(1).where(
                        self.crossref_model.item_id == self.item_model.id
                    )
                )
            )

            result = await session.execute(stmt)
            return list(result.scalars().all())