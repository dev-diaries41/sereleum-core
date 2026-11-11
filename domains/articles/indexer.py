from smartscan import StoredEmbedding
from smartscan.processor import BatchProcessor
from smartscan.providers import TextEmbeddingProvider

from domains.articles.item import Article

from sereleum.data.stores.item_embed_store import ItemEmbedStore


class ArticleIndexer(BatchProcessor[Article, tuple[StoredEmbedding, Article]]):
    def __init__(self, 
                text_encoder: TextEmbeddingProvider,
                item_embed_store: ItemEmbedStore[Article],
                max_chunks: int | None = None,
                **kwargs
                ):
        super().__init__(**kwargs)
        self.text_encoder = text_encoder
        self.max_chunks = max_chunks
        self.item_store = item_embed_store

    def on_process(self, item):
        text = f'[TITLE]: {item.title} \n[CONTENT]: {item.content}'
        embedding = self.text_encoder.embed(text)[0]
        return StoredEmbedding(item.id, embedding), item
             
    async def on_batch_complete(self, batch):
        if len(batch) == 0:
            return
        embeds, items = zip(*batch)
        await self.item_store.items.add(items)
        await self.item_store.embeds.add(embeds)
