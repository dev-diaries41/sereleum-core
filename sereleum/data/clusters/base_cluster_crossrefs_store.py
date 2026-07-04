from sereleum.data.base_store import BaseStore
from sereleum.schemas.cluster import ClusterCrossRef, ClusterCrossRefFilter
from typing import Optional


class BaseClusterCrossRefStore(
    BaseStore[ClusterCrossRef, ClusterCrossRefFilter]
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def add_filters(self, query: str, f: Optional[ClusterCrossRefFilter] = None):
        params = []

        if not f:
            return query, params

        if f.include_cluster_ids:
            params.append(f.include_cluster_ids)
            query += f" AND cluster_id = ANY(${len(params)})"

        if f.exclude_cluster_ids:
            params.append(f.exclude_cluster_ids)
            query += f" AND cluster_id != ALL(${len(params)})"

        return query, params