from pydantic import BaseModel
from typing_extensions import TypeVar, TypeAlias, Any
from sereleum.data.models import ItemBase, ClusterBase, ClusterCrossRefBase, TagBase, TagCrossRefBase
from sereleum.schemas.item import Item

TEntity = TypeVar("TEntity")
TDomain = TypeVar("TDomain", bound=BaseModel)

TPostgresItemModel = TypeVar("TPostgresItemModel", bound=ItemBase)

TPostgresClusterModel = TypeVar("TPostgresClusterModel", bound=ClusterBase)
TPostgresClusterCrossRefModel = TypeVar("TPostgresClusterCrossRefModel", bound=ClusterCrossRefBase)
TPostgresItemModel = TypeVar("TPostgresItemModel", bound=ItemBase)

TPostgresTagModel = TypeVar("TPostgresClusterModel", bound=TagBase)
TPostgresTagCrossRefModel = TypeVar("TPostgresTagCrossRefModel", bound=TagCrossRefBase)

TItem = TypeVar("TItem", bound=Item)
Filter: TypeAlias = dict[str, Any]