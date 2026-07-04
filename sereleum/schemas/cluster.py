from pydantic import BaseModel
from typing import Optional

class StoredClusterMetadata(BaseModel):
    id: str
    prototype_size: int
    label: str
    mean_similarity: float
    std_similarity: float

class ClusterFilter(BaseModel):
    label: Optional[str] = None
    size: Optional[int] = None


class ClusterCrossRef(BaseModel):
    item_id: str
    cluster_id: str

class ClusterCrossRefFilter(BaseModel):
    include_cluster_ids: Optional[list[str]] = None
    exclude_cluster_ids: Optional[list[str]] = None

