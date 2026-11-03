from typing import Protocol

from sereleum.data.stores.store import Store
from sereleum.schemas.tag import TagCrossRef

class TagCrossRefStore(Store[TagCrossRef], Protocol):
    pass