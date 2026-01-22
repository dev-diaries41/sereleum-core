from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, List
from smartscan import ClusterNoEmbeddings

class PromptMetadata(BaseModel):
    UNCLUSTERED: str = "unclustered"
    cluster_id: str = UNCLUSTERED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tokens: Optional[int] = None

class Prompt(BaseModel):
    prompt_id: str
    content: str
    metadata: PromptMetadata = Field(default_factory=PromptMetadata)

class PromptsOverviewInfo(BaseModel):
    total_prompts: int
    total_clusters: int
    top_clusters: List[ClusterNoEmbeddings]
    top_cluster_token_counts: Dict[str, int]

# Long running jobs
FinishedStatus = Literal['complete', 'failed']

Status = Literal[
    FinishedStatus,
    "active",
    "delayed",
    "queued",
]