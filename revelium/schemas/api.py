from pydantic import BaseModel
from typing import List, Optional, Literal, ClassVar

from smartscan import  ClusterMetadata, ClusterAccuracy

from revelium.types import Prompt, PromptsOverviewInfo, Status

# Websocksets / SSE
    
class ProgressMessage(BaseModel):
    progress: float

class ErrorMessage(BaseModel):
    error: str
    item: str

class FailMessage(BaseModel):
    error: str

class CompleteMessage(BaseModel):
    total_processed: int
    time_elapsed: float

class JobReceipt(BaseModel):
  status: Status
  job_id: str

# HTTP
class PromptsPayload(BaseModel):
    prompts: List[Prompt]


class AddPromptsRequest(PromptsPayload):
    pass

class AddPromptsResponse(JobReceipt):
    pass
 
class GetPromptsRequest(BaseModel):
    prompt_ids: Optional[List[str]] = None
    cluster_id: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None

class QueryPromptsRequest(BaseModel):
    query:str
    cluster_id: Optional[str] = None
    limit: Optional[int] = None

class GetPromptsResponse(PromptsPayload):
    pass

class GetPromptsOverviewResponse(PromptsOverviewInfo):
    pass

class GetCountResponse(BaseModel):
    count: int

class GetLabelsResponse(BaseModel):
    labels: List[str]

class GetClusterRequestParams(BaseModel):
    cluster_id: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class ClusterNoEmbeddings(BaseModel):
    UNLABELLED:ClassVar[str] = "unlabelled"
    prototype_id: str
    metadata: ClusterMetadata
    label: str
    
class GetClustersResponse(BaseModel):
    clusters: List[ClusterNoEmbeddings]

class GetClustersAccuracyResponse(BaseModel):
    accuracy: ClusterAccuracy


class UpdateLabelParams(BaseModel):
    cluster_id: str
    label: str

class UpdateLabelResponse(BaseModel):
    updated_label: str

class UpdatePromptClusterIdResponse(BaseModel):
    updated_cluster_id: str

class UpdatePromptClusterIdParams(BaseModel):
    prompt_id: str
    cluster_id: str
    