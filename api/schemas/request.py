from pydantic import BaseModel
from typing import List, Optional, Generic

from sereleum.data.types import TItem
from sereleum.collections.types import CollectionId

class AddItemsRequest(BaseModel,  Generic[TItem]):
    items: List[TItem]


class AddItemsRequestOptions(BaseModel):
    auto_label: bool 
    default_threshold: float

 
class GetItemsRequest(BaseModel):
    cluster_ids: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class GetItemsByIdRequest(BaseModel):
    item_ids: Optional[List[str]] = None


class QueryItemsRequest(BaseModel):
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
    item_id: str
    cluster_id: str

class MergeRequest(BaseModel):
    primary_collection_id: CollectionId
    secondary_collection_ids: List[CollectionId]
