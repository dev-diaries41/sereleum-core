from abc import ABC
from typing import Generic, Optional


from sqlalchemy import Select, delete, select, exists, func, literal, String, cast
from sqlalchemy.dialects.postgresql import insert, ARRAY

from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.schemas.tag import Tag
from sereleum.data.types import TPostgresTagCrossRefModel, TPostgresItemModel, TPostgresTagModel, Filter
from sereleum.enums.collections import CollectionType
from sereleum.schemas.collection import BaseCollection

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
                    self.model.name,
                    size_expr.label("size"),
                )
                .outerjoin(
                    self.crossref_model,
                    self.crossref_model.tag_id == self.model.id,
                )
                .group_by(self.model.id, self.model.name)
            )

            stmt = self.apply_filters(stmt, filter)

            if filter and (size := filter.get("size")) is not None:
                stmt = stmt.having(size_expr == size)

            column = (
                size_expr if order_by == "size"
                else getattr(self.model, order_by) if order_by
                else self.primary_keys[0]
            )

            stmt = stmt.order_by(
                column.asc() if ascending else column.desc()
            ).offset(offset)

            if limit is not None:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)

            return [
                BaseCollection(
                    id=row.id,
                    name=row.name,
                    size=row.size,
                    type=CollectionType.TAG,
                )
                for row in result.all()
            ]


    async def merge(self, primary_tag_id: int, secondary_tag_ids: list[int]) -> None:
        if not secondary_tag_ids:
            return

        async with self.sessionmaker() as session:
            source = (
                select(
                    self.crossref_model.item_id,
                    literal(primary_tag_id),
                )
                .where(
                    self.crossref_model.tag_id.in_(secondary_tag_ids),
                    self.crossref_model.tag_id != primary_tag_id,
                )
            )

            stmt = (
                insert(self.crossref_model)
                .from_select(["item_id", "tag_id"], source)
                .on_conflict_do_nothing(
                    index_elements=[
                        self.crossref_model.item_id,
                        self.crossref_model.tag_id,
                    ]
                )
            )

            await session.execute(stmt)
            await session.commit()



    async def tag(self, tag_name: str, item_ids: list[str]) -> None:
        if not item_ids:
            return

        async with self.sessionmaker() as session:
            tag_stmt = (
                insert(self.model)
                .values(name=tag_name)
                .on_conflict_do_update(
                    index_elements=[self.model.name],
                    set_={"name": self.model.name},
                )
                .returning(self.model.id)
                .cte("tag")
            )

            items = func.unnest(
                cast(literal(item_ids), ARRAY(String))
            ).table_valued("item_id").render_derived()

            stmt = (
                insert(self.crossref_model)
                .from_select(
                    ["item_id", "tag_id"],
                    select(items.c.item_id, tag_stmt.c.id),
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        self.crossref_model.item_id,
                        self.crossref_model.tag_id,
                    ]
                )
            )

            await session.execute(stmt)
            await session.commit()