from typing import Protocol

from sereleum.data.stores.store import Store
from sereleum.schemas.cluster import ClusterCrossRef
from sereleum.data.types import TEntity


class ClusterCrossRefStore(Store[TEntity, ClusterCrossRef], Protocol):
    pass