from typing import Protocol, TypeVar

from sereleum.data.stores.store import Store
from sereleum.schemas.cluster import ClusterCrossRef

TCrossRef = TypeVar("TCrossRef")

class ClusterCrossRefStore(Store[TCrossRef, ClusterCrossRef], Protocol):
    pass