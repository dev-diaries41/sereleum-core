from sereleum.data.entity import Entity, Index
from sereleum.schemas.cluster import StoredClusterMetadata


def make_cluster_entity(table: str):
    class ClusterEntity(Entity[StoredClusterMetadata]):
        model = StoredClusterMetadata
        table_name = table
        primary_key = "id"

        @property
        def indexes(self):
            return [
                Index(["prototype_size"])
            ]

    return ClusterEntity