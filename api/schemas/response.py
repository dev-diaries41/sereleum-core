from pydantic import BaseModel
from typing import List, Optional, Literal

from domains.prompts.prompt import Prompt, PromptsOverviewInfo
from sereleum.schemas.cluster import StoredClusterMetadata
from sereleum.types import Status

# Websocksets / SSE
class ProgressMessage(BaseModel):
    event: Literal["progress"] = "progress"
    progress: float

class ErrorMessage(BaseModel):
    event: Literal["error"] = "error"
    error: str
    item: str

class FailMessage(BaseModel):
    event: Literal["failed"] = "failed"
    error: str

class CompleteMessage(BaseModel):
    event: Literal["complete"] = "complete"
    total_processed: Optional[int] = None
    time_elapsed: Optional[float] = None

class ActiveMessage(BaseModel):
    event: Literal["active"] = "active"


# HTTP Response

class AddPromptsResponse(BaseModel):
    status: Status
    job_id: str


class GetPromptsResponse(BaseModel):
    prompts: List[Prompt]

class GetPromptsOverviewResponse(PromptsOverviewInfo):
    pass

class GetCountResponse(BaseModel):
    count: int

    
class GetClustersResponse(BaseModel):
    clusters: List[StoredClusterMetadata]


class RenameClusterResponse(BaseModel):
    updated_label: str

class MoveItemResponse(BaseModel):
    updated_cluster_id: str

    
class MergeResponse(BaseModel):
    updated_clusters: List[StoredClusterMetadata]
