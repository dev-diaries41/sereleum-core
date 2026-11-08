from pydantic import BaseModel

from sereleum.collections.types import CollectionId
from sereleum.enums.collections import CollectionType

class BaseCollection(BaseModel):
    id: CollectionId
    name: str
    size: int
    type: CollectionType