from abc import ABC

from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.schemas.cluster import ClusterCrossRef
from sereleum.data.types import Filter
from sereleum.data.models import ClusterCrossRefBase

from sqlalchemy import Select, select, func, literal, cast, String
from sqlalchemy.dialects.postgresql import insert, ARRAY

class PostgresClusterCrossRefStore(
    BasePostgresStore[ClusterCrossRefBase, ClusterCrossRef],
    ABC,
):

    def apply_filters(
        self,
        stmt: Select,
        f: Filter | None,
    ) -> Select:
        if not f:
            return stmt

        if (include_cluster_ids := f.get('include_cluster_ids')) is not None:
            stmt = stmt.where(self.model.cluster_id.in_(include_cluster_ids))

        if (exclude_cluster_ids := f.get('exclude_cluster_ids')) is not None:
            stmt = stmt.where( ~self.model.cluster_id.in_(exclude_cluster_ids) )
        return stmt


    async def move(
        self,
        destination_collection_id: str,
        source_collection_id: str,
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
                items_stmt = (
                    select(self.model.item_id)
                    .where(
                        self.model.cluster_id == source_collection_id,
                        ~self.model.item_id.in_(excluded_item_ids)
                        if excluded_item_ids
                        else True,
                    )
                )
            else:
                items_stmt = select(
                    func.unnest(
                        cast(literal(item_ids), ARRAY(String))
                    ).label("item_id")
                )

            stmt = (
                insert(self.model)
                .from_select(
                    ["item_id", "cluster_id"],
                    select(
                        items_stmt.subquery("items").c.item_id,
                        literal(destination_collection_id),
                    ),
                )
                .on_conflict_do_update(
                    index_elements=[self.model.item_id],
                    set_={"cluster_id": destination_collection_id},
                )
            )

            await session.execute(stmt)
            await session.commit()