from pydantic import BaseModel
from typing import TypeVar
from sereleum.data.models.cluster_base import ClusterBase
from sereleum.data.models.cluster_crossref_base import ClusterCrossRefBase
from sereleum.data.models.item_base import ItemBase
from sereleum.data.stores.item_store import ItemStore
from sereleum.data.stores.cluster_store import ClusterStore
from sereleum.data.stores.cluster_crossref_store import ClusterCrossRefStore
from sereleum.schemas.item import Item

TEntity = TypeVar("TEntity")
TDomain = TypeVar("TDomain", bound=BaseModel)

TPostgresClusterModel = TypeVar("TPostgresClusterModel", bound=ClusterBase)
TPostgresCrossRefModel = TypeVar("TPostgresCrossRefModel", bound=ClusterCrossRefBase)
TPostgresItemModel = TypeVar("TPostgresItemModel", bound=ItemBase)

TItem = TypeVar("TItem", bound=Item)
TClusterStore = TypeVar("TClusterStore", bound=ClusterStore)
TClusterCrossRefStore = TypeVar("TClusterCrossRefStore", bound=ClusterCrossRefStore)
TItemStore = TypeVar("TItemStore", bound=ItemStore)
