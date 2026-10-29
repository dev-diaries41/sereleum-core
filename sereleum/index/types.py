from typing import TypeAlias
from smartscan.processor.processor import BatchProcessor
from sereleum.data.types import TItem
from smartscan.embeds.types import StoredEmbedding

Indexer: TypeAlias = BatchProcessor[TItem, tuple[StoredEmbedding, TItem]]