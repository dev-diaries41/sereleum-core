from abc import ABC
from pydantic import BaseModel
from typing import Generic, Optional

from sqlalchemy import Select, delete, select, exists, func

from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.schemas.cluster import StoredClusterMetadata
from sereleum.data.types import TPostgresClusterModel, TPostgresItemModel, TPostgresClusterCrossRefModel, Filter
from sereleum.enums.collections import CollectionType
from sereleum.schemas.collection import BaseCollection

class PostgresClusterStore(
    Generic[TPostgresClusterModel, TPostgresClusterCrossRefModel, TPostgresItemModel],
    BasePostgresStore[TPostgresClusterModel, StoredClusterMetadata],
    ABC,
):
    item_model: type[TPostgresItemModel]
    crossref_model: type[TPostgresClusterCrossRefModel]


    def apply_filters(self, stmt: Select, f: Filter | None) -> Select:
        if not f:
            return stmt

        if (ids := f.get("ids")) is not None:
            stmt = stmt.where(self.model.id.in_(ids))

        if (label := f.get("label")) is not None:
            stmt = stmt.where(self.model.label == label)

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


    async def get_collections(
            self,
            filter: Optional[Filter] = None,
            limit: Optional[int] = None,
            offset: int = 0,
            order_by: Optional[str] = None,
            ascending: bool = True,
            ) -> list[BaseCollection]:
        async with self.sessionmaker() as session:
            size_expr = func.count(self.crossref_model.item_id)

            stmt = (
                select(
                    self.model.id,
                    self.model.label,
                    size_expr.label("size"),
                )
                .outerjoin(
                    self.crossref_model,
                    self.crossref_model.cluster_id == self.model.id,
                )
                .group_by(self.model.id, self.model.label)
            )

            stmt = self.apply_filters(stmt, filter)

            if filter and (size := filter.get("size")) is not None:
                stmt = stmt.having(size_expr == size)

            column = getattr(self.model, order_by) if order_by else self.primary_keys[0]
            stmt = stmt.order_by(column.asc() if ascending else column.desc()).offset(offset)

            if limit is not None:
                stmt = stmt.limit(limit)
                
            result = await session.execute(stmt)

            return [
                BaseCollection(
                    id=row.id,
                    name=row.label or row.id,
                    size=row.size,
                    type=CollectionType.CLUSTER,
                )
                for row in result.all()
            ]