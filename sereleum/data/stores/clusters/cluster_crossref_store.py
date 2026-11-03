from typing import Protocol

from sereleum.data.stores.store import Store
from sereleum.schemas.cluster import ClusterCrossRef

class ClusterCrossRefStore(Store[ClusterCrossRef], Protocol):
    pass