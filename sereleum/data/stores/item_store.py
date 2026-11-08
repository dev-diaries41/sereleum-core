from typing import Protocol

from sereleum.data.stores.store import Store
from sereleum.data.types import TItem

class ItemStore(Store[TItem], Protocol):
    pass