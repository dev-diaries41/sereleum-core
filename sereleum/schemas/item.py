
from pydantic import BaseModel
from typing import List 
from sereleum.schemas.collection import BaseCollection

class Item(BaseModel):
    id: str

class ItemsOverviewInfo(BaseModel):
    total_items: int
    total_clusters: int
    total_tags: int
    top_clusters: List[BaseCollection]
    top_tags: List[BaseCollection]