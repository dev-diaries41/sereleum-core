
from pydantic import BaseModel
from typing import List 
from sereleum.schemas.cluster import StoredClusterMetadata

class Item(BaseModel):
    id: str

class ItemsOverviewInfo(BaseModel):
    total_items: int
    total_clusters: int
    top_clusters: List[StoredClusterMetadata]