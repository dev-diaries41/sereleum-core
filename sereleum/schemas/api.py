from pydantic import BaseModel
from typing import List, Optional

from smartscan import  ClusterNoEmbeddings, ClusterMerges

from sereleum.schemas.items.prompt import Prompt, PromptsOverviewInfo
from sereleum.types import Status

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
    cluster_ids: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None

class QueryPromptsRequest(BaseModel):
    query:str
    cluster_ids: Optional[List[str]] = None
    limit: Optional[int] = None

class GetPromptsResponse(PromptsPayload):
    pass

class GetPromptsOverviewResponse(PromptsOverviewInfo):
    pass

class GetCountResponse(BaseModel):
    count: int


class GetClusterRequestParams(BaseModel):
    cluster_id: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None

    
class GetClustersResponse(BaseModel):
    clusters: List[ClusterNoEmbeddings]


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

class MergeClustersRequest(BaseModel):
    merges: ClusterMerges

    
class MergeResponse(BaseModel):
    updated_clusters: List[ClusterNoEmbeddings]


class ClusterOptionsForm(BaseModel):
    auto_label: bool 
    default_threshold: float