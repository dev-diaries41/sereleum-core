from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore

class PromptEmbedStore(PgVectorEmbeddingStore):
    table_name = "prompt_embeds"