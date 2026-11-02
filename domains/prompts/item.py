from datetime import datetime, timezone
from pydantic import Field
from typing import Optional, Dict

from sereleum.schemas.item import Item, ItemsOverviewInfo

class Prompt(Item):
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tokens: Optional[int] = None

class PromptsOverviewInfo(ItemsOverviewInfo):
    top_cluster_token_counts: Dict[str, int]
