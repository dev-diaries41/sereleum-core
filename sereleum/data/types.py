from pydantic import BaseModel
from typing import TypeVar
from sereleum.schemas.items.item import Item

TItem = TypeVar("TItem", bound=Item)
TItemFilter = TypeVar("TItemFilter", bound=BaseModel)
