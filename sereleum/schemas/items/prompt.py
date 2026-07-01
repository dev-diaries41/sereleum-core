from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, ClassVar
from smartscan import ClusterNoEmbeddings
from sereleum.schemas.items.item import Item

class PromptMetadata(BaseModel):
    UNCLUSTERED: ClassVar = "unclustered"
    cluster_id: str = UNCLUSTERED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tokens: Optional[int] = None

class Prompt(Item[str, PromptMetadata]):
    metadata: PromptMetadata = Field(default_factory=PromptMetadata)

class PromptsOverviewInfo(BaseModel):
    total_prompts: int
    total_clusters: int
    top_clusters: List[ClusterNoEmbeddings]
    top_cluster_token_counts: Dict[str, int]
