from typing import Literal, TypeAlias, TypeVar
from pydantic import BaseModel
from smartscan.types import LocalTextEmbeddingModel

TextEmbeddingModel: TypeAlias = Literal[
    LocalTextEmbeddingModel,
    "text-embedding-3-small",
    "text-embedding-3-large",
]
