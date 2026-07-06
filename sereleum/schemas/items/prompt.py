from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional, Dict, List

from sereleum.schemas.items.item import Item, BaseItemFilter
from sereleum.schemas.cluster import StoredClusterMetadata

class Prompt(Item):
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tokens: Optional[int] = None

class PromptFilter(BaseItemFilter):
    min_tokens: Optional[int] = None
    max_tokens: Optional[int] = None
 
class PromptsOverviewInfo(BaseModel):
    total_prompts: int
    total_clusters: int
    top_clusters: List[StoredClusterMetadata]
    top_cluster_token_counts: Dict[str, int]
