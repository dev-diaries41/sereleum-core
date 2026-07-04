from openai.types import ResponsesModel
from smartscan import StoredEmbedding
from smartscan.media import chunk_text
from smartscan.embeds import generate_prototype_embedding, EmbeddingStore
from smartscan.processor import BatchProcessor
from smartscan.providers import TextEmbeddingProvider
from sereleum.schemas.items.prompt import Prompt
from sereleum.utils.tokens import count_tokens_embedding
from sereleum.data.prompts.prompt_store import PromptStore

class PromptIndexer(BatchProcessor[Prompt, tuple[StoredEmbedding, Prompt]]):
    def __init__(self, 
                text_encoder: TextEmbeddingProvider,
                embeddings_store: EmbeddingStore,
                prompt_store: PromptStore,
                max_chunks: int | None = None,
                prompt_model: str | ResponsesModel = "gpt-5-mini",
                **kwargs
                ):
        super().__init__(**kwargs)
        self.text_encoder = text_encoder
        self.max_chunks = max_chunks
        self.max_tokenizer_length = text_encoder.max_tokenizer_length
        self.embeddings_store = embeddings_store
        self.prompt_model = prompt_model
        self.prompt_store = prompt_store

    # All chunks share the same item_id (url or file) so that chunks are group
    # In the on_batch_complete method, the listener can handle use it as metaddata and assign unique ids to each chunk if required
    def on_process(self, item):
        tokens = count_tokens_embedding(item.content, self.prompt_model)
        chunks = chunk_text(item.content, self.max_tokenizer_length)
        embeddings = self.text_encoder.embed_batch(chunks)
        text_prototype = generate_prototype_embedding(embeddings)
        item.tokens = tokens
        return StoredEmbedding(item.id, text_prototype), item
             
    async def on_batch_complete(self, batch):
        if len(batch) == 0:
            return
        embeds, prompts = zip(*batch)
        await self.embeddings_store.add(embeds)
        await self.prompt_store.add(prompts)
