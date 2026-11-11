from typing import Generic

from sereleum.data.stores.item_store import ItemStore
from sereleum.data.types import TItem

from smartscan.embeds.embedding_store import EmbeddingStore


class ItemEmbedStore(Generic[TItem]):
    def __init__(self, items: ItemStore[TItem], embeds: EmbeddingStore):
        self.items = items
        self.embeds = embeds