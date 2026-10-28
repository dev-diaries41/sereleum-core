from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore

class PromptClusterEmbedStore(PgVectorEmbeddingStore):
    table_name = "prompt_cluster_embeds"