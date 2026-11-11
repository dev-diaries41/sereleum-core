from abc import ABC
from typing import Optional


from sqlalchemy import Select, delete, select, func, literal, String, cast, true
from sqlalchemy.dialects.postgresql import insert, ARRAY

from sereleum.collections.types import CollectionId
from sereleum.data.models import ItemBase, ClusterCrossRefBase, TagBase, TagCrossRefBase
from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.schemas.tag import Tag
from sereleum.data.types import Filter
from sereleum.enums.collections import CollectionType
from sereleum.schemas.collection import BaseCollection

class PostgresTagStore(
    BasePostgresStore[TagBase, Tag],
    ABC,
):
    item_model: type[ItemBase]
    tag_crossref_model: type[TagCrossRefBase]
    cluster_crossref_model: type[ClusterCrossRefBase]

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
            size_expr = func.count(self.tag_crossref_model.item_id)

            stmt = (
                select(
                    self.model.id,
                    self.model.name,
                    size_expr.label("size"),
                )
                .outerjoin(
                    self.tag_crossref_model,
                    self.tag_crossref_model.tag_id == self.model.id,
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
                    self.tag_crossref_model.item_id,
                    literal(primary_tag_id),
                )
                .where(
                    self.tag_crossref_model.tag_id.in_(secondary_tag_ids),
                    self.tag_crossref_model.tag_id != primary_tag_id,
                )
            )

            stmt = (
                insert(self.tag_crossref_model)
                .from_select(["item_id", "tag_id"], source)
                .on_conflict_do_nothing(
                    index_elements=[
                        self.tag_crossref_model.item_id,
                        self.tag_crossref_model.tag_id,
                    ]
                )
            )

            await session.execute(stmt)

            await session.execute(
                        delete(self.model).where(
                            self.model.id.in_(secondary_tag_ids)
                        )
                    )
            await session.commit()


    async def tag(
        self,
        tag_name: str,
        collection_id: CollectionId | None = None,
        item_ids: list[str] | None = None,
        *,
        select_all: bool = False,
        excluded_item_ids: list[str] | None = None,
    ) -> None:
        item_ids = item_ids or []
        excluded_item_ids = excluded_item_ids or []

        # This is only acceptable because items are currently always accessed through a collection in the app.
        if select_all and collection_id is None:
            raise ValueError("collection_id is required when select_all=True")

        if not select_all and not item_ids:
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

            if select_all:
                exclusion = (
                    ~self.item_model.id.in_(excluded_item_ids)
                    if excluded_item_ids
                    else True
                )

                if isinstance(collection_id, int):
                    items_stmt = (
                        select(self.item_model.id.label("item_id"))
                        .join(
                            self.tag_crossref_model,
                            self.tag_crossref_model.item_id == self.item_model.id,
                        )
                        .where(
                            self.tag_crossref_model.tag_id == collection_id,
                            exclusion,
                        )
                    )
                else:
                    items_stmt = (
                        select(self.item_model.id.label("item_id"))
                        .join(
                            self.cluster_crossref_model,
                            self.cluster_crossref_model.item_id == self.item_model.id,
                        )
                        .where(
                            self.cluster_crossref_model.cluster_id == collection_id,
                            exclusion,
                        )
                    )
                items = items_stmt.subquery("items")
            else:
                items = func.unnest(
                    cast(literal(item_ids), ARRAY(String))
                ).table_valued("item_id").render_derived()

                stmt = (
                insert(self.tag_crossref_model)
                .from_select(
                    ["item_id", "tag_id"],
                    select(items.c.item_id, tag_stmt.c.id).select_from(
                        items.join(tag_stmt, true())
                    ),
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        self.tag_crossref_model.item_id,
                        self.tag_crossref_model.tag_id,
                    ]
                )
            )

            await session.execute(stmt)
            await session.commit()


    async def untag(
        self,
        tag_id: int,
        item_ids: list[str] | None = None,
        *,
        select_all: bool = False,
        excluded_item_ids: list[str] | None = None,
    ) -> None:
        item_ids = item_ids or []
        excluded_item_ids = excluded_item_ids or []

        if not select_all and not item_ids:
            return

        async with self.sessionmaker() as session:
            if select_all:
                exclusion = (
                    ~self.item_model.id.in_(excluded_item_ids)
                    if excluded_item_ids
                    else True
                )
                items_stmt = select(self.item_model.id).where(exclusion)
                item_filter = self.tag_crossref_model.item_id.in_(items_stmt)
            else:
                item_filter = self.tag_crossref_model.item_id.in_(item_ids)

            stmt = delete(self.tag_crossref_model).where(
                self.tag_crossref_model.tag_id == tag_id,
                item_filter,
            )

            await session.execute(stmt)
            await session.commit()