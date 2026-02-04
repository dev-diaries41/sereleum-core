from typing import Literal, TypeAlias
from smartscan.types import LocalTextEmbeddingModel

TextEmbeddingModel: TypeAlias = Literal[
    LocalTextEmbeddingModel,
    "text-embedding-3-small",
    "text-embedding-3-large",
]
