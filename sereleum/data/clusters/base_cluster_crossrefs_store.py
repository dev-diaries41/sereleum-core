from abc import ABC

from sqlalchemy import Select

from sereleum.data.base_store import BaseStore
from sereleum.schemas.cluster import ClusterCrossRefFilter
from sereleum.data.types import TCrossRefModel


class BaseClusterCrossRefStore(
    BaseStore[TCrossRefModel, ClusterCrossRefFilter],
    ABC,
):
    primary_key = "item_id"

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