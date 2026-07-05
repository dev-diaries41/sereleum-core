from abc import ABC

from sqlalchemy import Select

from sereleum.data.base_store import BaseStore
from sereleum.schemas.cluster import ClusterFilter
from sereleum.data.types import TClusterModel

class BaseClusterStore(
    BaseStore[TClusterModel, ClusterFilter],
    ABC,
):
    def apply_filters(
        self,
        stmt: Select,
        f: ClusterFilter | None,
    ) -> Select:
        if not f:
            return stmt

        if f.label is not None:
            stmt = stmt.where(self.model.label == f.label)

        if f.size is not None:
            stmt = stmt.where(
                self.model.prototype_size == f.size
            )

        return stmt