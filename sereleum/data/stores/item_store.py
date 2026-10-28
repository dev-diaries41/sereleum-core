from typing import Protocol, TypeVar

from sereleum.data.stores.store import Store
from sereleum.schemas.cluster import StoredClusterMetadata

TItem = TypeVar("TItem")

class ItemStore(Store[TItem, StoredClusterMetadata], Protocol):
    pass