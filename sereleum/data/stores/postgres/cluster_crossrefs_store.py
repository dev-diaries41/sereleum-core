from abc import ABC
from typing import Generic

from sqlalchemy import Select

from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.schemas.cluster import ClusterCrossRefFilter, ClusterCrossRef
from sereleum.data.types import TPostgresCrossRefModel


class PostgresClusterCrossRefStore(
    Generic[TPostgresCrossRefModel],
    BasePostgresStore[TPostgresCrossRefModel, ClusterCrossRef],
    ABC,
):

    def apply_filters(
        self,
        stmt: Select,
        f: ClusterCrossRefFilter | None,
    ) -> Select:
        if not f:
            return stmt

        if f.include_cluster_ids:
            stmt = stmt.where(
                self.model.cluster_id.in_(f.include_cluster_ids)
            )

        if f.exclude_cluster_ids:
            stmt = stmt.where(
                ~self.model.cluster_id.in_(f.exclude_cluster_ids)
            )

        return stmt