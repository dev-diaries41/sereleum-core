
from pydantic import BaseModel
from typing import Optional,List 
from datetime import date

class Item(BaseModel):
    id: str

class BaseItemFilter(BaseModel):
    cluster_ids: Optional[List[str]] = None
    created_after: Optional[date] = None
    created_before: Optional[date] = None
    updated_after: Optional[date] = None
    updated_before: Optional[date] = None
