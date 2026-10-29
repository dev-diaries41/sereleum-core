from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore

from domains.articles.item import Article
from domains.articles.stores import ArticleStore, ArticleClusterStore, ArticleClusterCrossRefStore

from sqlalchemy.ext.asyncio import async_sessionmaker
from llm_connect.providers.llm_provider import LLMProvider


def get_cluster_manager(sessionmaker: async_sessionmaker, embed_dim:int, llm: LLMProvider):
    item_store = ArticleStore(sessionmaker)
    cluster_store = ArticleClusterStore(sessionmaker)
    cluster_crossref_store = ArticleClusterCrossRefStore(sessionmaker)
    item_embed_store = PgVectorEmbeddingStore(name='article_embeds', sessionmaker=sessionmaker, dim=embed_dim)
    cluster_embed_store = PgVectorEmbeddingStore(name='article_cluster_embeds', sessionmaker=sessionmaker, dim=embed_dim)
    return ClusterManager[Article](
        cluster_embedding_store=cluster_embed_store,
        cluster_store=cluster_store,
        crossrefs_store=cluster_crossref_store,
        item_embedding_store=item_embed_store, 
        item_store=item_store,
        llm=llm,
    )