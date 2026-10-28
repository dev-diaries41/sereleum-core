from typing import Protocol, TypeVar

from sereleum.data.stores.store import Store
from sereleum.data.types import TItem, TEntity

class ItemStore(Store[TEntity, TItem], Protocol):
    pass