from sereleum.data.entity import Entity, Index, ForeignKey
from sereleum.schemas.cluster import ClusterCrossRef

def make_cluster_crossref_entity(
    table: str,
    cluster_entity: type[Entity],
    item_entity: type[Entity],
):

    class ClusterCrossRefEntity(Entity[ClusterCrossRef]):
        model = ClusterCrossRef
        table_name = table
        primary_key = "item_id"

        @property
        def indexes(self):
            return [Index(["cluster_id"])]

        @property
        def foreign_keys(self):
            return [
                ForeignKey(
                    column="cluster_id",
                    references=cluster_entity,
                    references_column="id",
                ),
                ForeignKey(
                    column="item_id",
                    references=item_entity,
                    references_column="id",
                ),
            ]

    return ClusterCrossRefEntity