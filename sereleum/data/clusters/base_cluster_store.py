from typing import Optional

from sereleum.data.base_store import BaseStore
from sereleum.schemas.cluster import StoredClusterMetadata, ClusterFilter

class BaseClusterStore(BaseStore[StoredClusterMetadata, ClusterFilter]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def add_filters(self, query: str, f: Optional[ClusterFilter] = None):
        params = []

        if not f:
            return query, params

        if f.label is not None:
            params.append(f.label)
            query += f" AND label = ${len(params)}"

        if f.size is not None:
            params.append(f.size)
            query += f" AND prototype_size = ${len(params)}"

        return query, params