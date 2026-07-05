from pydantic import BaseModel
from typing import TypeVar
from sereleum.data.base import Base

TItemModel = TypeVar("TItemModel", bound=Base)
TQueryFilter = TypeVar("TQueryFilter", bound=BaseModel)
TCrossRefModel = TypeVar("TCrossRefModel", bound=Base)
TClusterModel = TypeVar("TClusterModel", bound=Base)
