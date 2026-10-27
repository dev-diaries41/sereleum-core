from pydantic import BaseModel
from typing import TypeVar
from sereleum.data.models.base import Base
from sereleum.data.models.cluster_base import ClusterBase
from sereleum.data.models.cluster_crossref_base import ClusterCrossRefBase

TCrossRefModel = TypeVar("TCrossRefModel", bound=ClusterCrossRefBase)
TClusterModel = TypeVar("TClusterModel", bound=ClusterBase)
TEntity = TypeVar("TEntity", bound=Base)
TDomain = TypeVar("TDomain", bound=BaseModel)