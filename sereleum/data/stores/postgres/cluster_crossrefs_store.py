from abc import ABC
from typing import Generic

from sqlalchemy import Select

from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.schemas.cluster import ClusterCrossRef
from sereleum.data.types import TPostgresClusterCrossRefModel, Filter


class PostgresClusterCrossRefStore(
    Generic[TPostgresClusterCrossRefModel],
    BasePostgresStore[TPostgresClusterCrossRefModel, ClusterCrossRef],
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