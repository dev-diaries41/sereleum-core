from pydantic import BaseModel
from typing import List, Optional

from smartscan import  ClusterMerges

from domains.prompts.prompt import Prompt
from sereleum.schemas.cluster import StoredClusterMetadata

class AddPromptsRequest(BaseModel):
    prompts: List[Prompt]


class AddPromptsRequestOptions(BaseModel):
    auto_label: bool 
    default_threshold: float

 
class GetPromptsRequest(BaseModel):
    cluster_ids: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class GetPromptsByIdsRequest(BaseModel):
    prompt_ids: Optional[List[str]] = None


class QueryPromptsRequest(BaseModel):
    query:str
    cluster_ids: Optional[List[str]] = None
    limit: Optional[int] = None


class GetClusterRequestParams(BaseModel):
    cluster_id: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None

class RenameClusterRequest(BaseModel):
    cluster_id: str
    label: str


class MoveItemRequest(BaseModel):
    prompt_id: str
    cluster_id: str

class MergeClustersRequest(BaseModel):
    merges: ClusterMerges
