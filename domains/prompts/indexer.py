from openai.types import ResponsesModel
from smartscan import StoredEmbedding
from smartscan.media import chunk_text
from smartscan.embeds import generate_prototype_embedding, EmbeddingStore
from smartscan.processor import BatchProcessor
from smartscan.providers import TextEmbeddingProvider
from domains.prompts.item import Prompt
from sereleum.utils.tokens import count_tokens_embedding
from sereleum.data.stores.item_store import ItemStore

from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore
from domains.prompts.item import Prompt
from domains.prompts.stores import PromptStore
from sqlalchemy.ext.asyncio import async_sessionmaker

class PromptIndexer(BatchProcessor[Prompt, tuple[StoredEmbedding, Prompt]]):
    def __init__(self, 
                text_encoder: TextEmbeddingProvider,
                embeddings_store: EmbeddingStore,
                prompt_store: ItemStore[Prompt],
                max_chunks: int | None = None,
                prompt_model: str | ResponsesModel = "gpt-5-mini",
                **kwargs
                ):
        super().__init__(**kwargs)
        self.text_encoder = text_encoder
        self.max_chunks = max_chunks
        self.embeddings_store = embeddings_store
        self.prompt_model = prompt_model
        self.prompt_store = prompt_store

    def on_process(self, item):
        tokens = count_tokens_embedding(item.content, self.prompt_model)
        chunks = chunk_text(item.content, self.text_encoder.max_tokens)
        embeddings = self.text_encoder.embed(chunks)
        text_prototype = generate_prototype_embedding(embeddings)
        item.tokens = tokens
        return StoredEmbedding(item.id, text_prototype), item
             
    async def on_batch_complete(self, batch):
        if len(batch) == 0:
            return
        embeds, prompts = zip(*batch)
        await self.prompt_store.add(prompts)
        await self.embeddings_store.add(embeds)


def create_indexer(
        text_embedder: TextEmbeddingProvider, 
        sessionmaker: async_sessionmaker,
        collection_name: str = 'prompts',
        **kwargs,
) -> PromptIndexer:
    return PromptIndexer(
        text_encoder=text_embedder,
        embeddings_store=PgVectorEmbeddingStore(name=f'{collection_name}_embeds', sessionmaker=sessionmaker),
        prompt_store=PromptStore(sessionmaker),
        **kwargs,
    )