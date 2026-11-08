from pydantic import BaseModel

class StoredClusterMetadata(BaseModel):
    id: str
    prototype_size: int
    label: str | None
    mean_similarity: float
    std_similarity: float


class ClusterCrossRef(BaseModel):
    item_id: str
    cluster_id: str