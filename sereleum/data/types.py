from pydantic import BaseModel
from typing import TypeVar
from sereleum.data.models.base import Base
from sereleum.data.models.cluster_base import ClusterBase
from sereleum.data.models.cluster_crossref_base import ClusterCrossRefBase

from sereleum.data.base_store import BaseStore
from sereleum.data.clusters.base_cluster_crossrefs_store import BaseClusterCrossRefStore
from sereleum.data.clusters.base_cluster_store import BaseClusterStore

TCrossRefModel = TypeVar("TCrossRefModel", bound=ClusterCrossRefBase)
TClusterModel = TypeVar("TClusterModel", bound=ClusterBase)
TEntity = TypeVar("TEntity", bound=Base) # Bound to BaseItem
TDomain = TypeVar("TDomain", bound=BaseModel)

TItemStore = TypeVar("TItemStore", bound=BaseStore) # TODO: create BaseItem
TClusterStore = TypeVar("TClusterStore", bound=BaseClusterStore)
TClusterCrossRefStore = TypeVar("TClusterCrossRefStore", bound=BaseClusterCrossRefStore)
