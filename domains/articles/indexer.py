from smartscan import StoredEmbedding
from smartscan.embeds import EmbeddingStore
from smartscan.processor import BatchProcessor
from smartscan.providers import TextEmbeddingProvider
from domains.articles.stores import ArticleStore
from domains.articles.item import Article
from sereleum.data.stores.item_store import ItemStore

from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore
from domains.articles.item import Article
from domains.articles.stores import ArticleStore
from sqlalchemy.ext.asyncio import async_sessionmaker


class ArticleIndexer(BatchProcessor[Article, tuple[StoredEmbedding, Article]]):
    def __init__(self, 
                text_encoder: TextEmbeddingProvider,
                embed_store: EmbeddingStore,
                item_store: ItemStore[Article],
                max_chunks: int | None = None,
                **kwargs
                ):
        super().__init__(**kwargs)
        self.text_encoder = text_encoder
        self.max_chunks = max_chunks
        self.embed_store = embed_store
        self.item_store = item_store

    def on_process(self, item):
        text = f'[TITLE]: {item.title} \n[CONTENT]: {item.content}'
        embedding = self.text_encoder.embed(text)[0]
        return StoredEmbedding(item.id, embedding), item
             
    async def on_batch_complete(self, batch):
        if len(batch) == 0:
            return
        embeds, prompts = zip(*batch)
        await self.item_store.add(prompts)
        await self.embed_store.add(embeds)



def create_indexer(
        text_embedder: TextEmbeddingProvider, 
        sessionmaker: async_sessionmaker,
        collection_name: str = 'articles',
        **kwargs,
        ) -> ArticleIndexer:
    return ArticleIndexer(
        text_encoder=text_embedder,
        embed_store=PgVectorEmbeddingStore(name=f'{collection_name}_embeds', sessionmaker=sessionmaker),
        item_store=ArticleStore(sessionmaker),
        **kwargs,
    )