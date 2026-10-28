from pydantic import BaseModel
from typing import TypeVar
from sereleum.data.models.cluster_base import ClusterBase
from sereleum.data.models.cluster_crossref_base import ClusterCrossRefBase
from sereleum.data.models.item_base import ItemBase
from sereleum.data.stores.item_store import ItemStore
from sereleum.data.stores.cluster_store import ClusterStore
from sereleum.data.stores.cluster_crossref_store import ClusterCrossRefStore

TEntity = TypeVar("TEntity")
TDomain = TypeVar("TDomain", bound=BaseModel)

TCrossRefModel = TypeVar("TCrossRefModel", bound=ClusterCrossRefBase)
TClusterModel = TypeVar("TClusterModel", bound=ClusterBase)
TItemModel = TypeVar("TClusterModel", bound=ItemBase)

TClusterStore = TypeVar("TClusterStore", bound=ClusterStore)
TClusterCrossRefStore = TypeVar("TClusterCrossRefStore", bound=ClusterCrossRefStore)
TItemStore = TypeVar("TItemStore", bound=ItemStore)
