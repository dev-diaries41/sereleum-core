
from pydantic import BaseModel
from typing import Optional,List 
from datetime import date

from sereleum.schemas.cluster import StoredClusterMetadata

class Item(BaseModel):
    id: str

class BaseItemFilter(BaseModel):
    ids: Optional[List[str]] = None
    cluster_ids: Optional[List[str]] = None
    created_after: Optional[date] = None
    created_before: Optional[date] = None
    updated_after: Optional[date] = None
    updated_before: Optional[date] = None


class ItemsOverviewInfo(BaseModel):
    total_prompts: int
    total_clusters: int
    top_clusters: List[StoredClusterMetadata]