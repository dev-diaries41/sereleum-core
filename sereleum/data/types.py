from pydantic import BaseModel
from typing import TypeVar
from sereleum.data.models.base import Base
from sereleum.data.models.cluster_base import ClusterBase
from sereleum.data.models.cluster_crossref_base import ClusterCrossRefBase
from sereleum.data.models.item_base import ItemBase


from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.data.stores.postgres.cluster_crossrefs_store import PostgresClusterCrossRefStore
from sereleum.data.stores.postgres.cluster_store import PostgresClusterStore

TEntity = TypeVar("TEntity")
TDomain = TypeVar("TDomain", bound=BaseModel)

TCrossRefModel = TypeVar("TCrossRefModel", bound=ClusterCrossRefBase)
TClusterModel = TypeVar("TClusterModel", bound=ClusterBase)
TItemModel = TypeVar("TClusterModel", bound=ItemBase)

TItemStore = TypeVar("TItemStore", bound=BasePostgresStore)
TClusterStore = TypeVar("TClusterStore", bound=PostgresClusterStore)
TClusterCrossRefStore = TypeVar("TClusterCrossRefStore", bound=PostgresClusterCrossRefStore)
