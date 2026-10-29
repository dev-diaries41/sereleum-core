from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore

class ArticleClusterEmbedStore(PgVectorEmbeddingStore):
    table_name = "article_cluster_embeds"