
from typing import Dict, TypeVar, Any, Generic
from pydantic import BaseModel

TItem = TypeVar("TItem", bound=Any)
TData = TypeVar("TData", bound=Any)
TMetadata = TypeVar("TMetadata", bound=Dict)

class Item(BaseModel, Generic[TData, TMetadata]):
    id: str
    data: TData
    metadata: TMetadata


