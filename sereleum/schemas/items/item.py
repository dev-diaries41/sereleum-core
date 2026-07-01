
from typing import Generic
from smartscan.types import TData, TItem, TMetadata
from pydantic import BaseModel


class Item(BaseModel, Generic[TData, TMetadata]):
    id: str
    data: TData
    metadata: TMetadata