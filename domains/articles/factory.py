from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore
from sereleum.label.cluster_labeller import ClusterLabeller
from sereleum.tags.tag_manager import TagManager
from sereleum.data.stores.item_embed_store import ItemEmbedStore

from domains.articles.item import Article
from domains.articles.stores import ArticleStore, ArticleClusterStore, ArticleClusterCrossRefStore, ArticleTagStore, ArticleTagCrossRefStore
from domains.articles.indexer import ArticleIndexer

from sqlalchemy.ext.asyncio import async_sessionmaker

from llm_connect.providers.llm_provider import LLMProvider

from smartscan.providers import TextEmbeddingProvider


def create_item_embed_store(sessionmaker):
    return ItemEmbedStore(
        items= ArticleStore(sessionmaker),
        embeds=PgVectorEmbeddingStore(name=f'articles_embeds', sessionmaker=sessionmaker)
    )

def create_cluster_manager( sessionmaker: async_sessionmaker, llm: LLMProvider | None = None, ):
    labeller = ClusterLabeller(llm=llm) if llm else None
    cluster_store = ArticleClusterStore(sessionmaker)
    cluster_crossref_store = ArticleClusterCrossRefStore(sessionmaker)
    cluster_embed_store = PgVectorEmbeddingStore(name=f'articles_cluster_embeds', sessionmaker=sessionmaker)
    item_embed_store = create_item_embed_store(sessionmaker=sessionmaker)

    return ClusterManager[Article](
        cluster_embedding_store=cluster_embed_store,
        cluster_store=cluster_store,
        crossrefs_store=cluster_crossref_store,
        item_store=item_embed_store,
        labeller=labeller,
    )


def create_tag_manager(sessionmaker: async_sessionmaker):
    tag_store = ArticleTagStore(sessionmaker)
    tag_crossref_store = ArticleTagCrossRefStore(sessionmaker)

    return TagManager(
        tag_store=tag_store,
        crossrefs_store=tag_crossref_store,
    )


def create_indexer( text_embedder: TextEmbeddingProvider, sessionmaker: async_sessionmaker, **kwargs) -> ArticleIndexer:
    item_embed_store = create_item_embed_store(sessionmaker=sessionmaker)

    return ArticleIndexer(
        text_encoder=text_embedder,
        item_store=item_embed_store,
        **kwargs
    )