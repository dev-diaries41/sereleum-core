from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore

class ArticleEmbedStore(PgVectorEmbeddingStore):
    table_name = "article_embeds"