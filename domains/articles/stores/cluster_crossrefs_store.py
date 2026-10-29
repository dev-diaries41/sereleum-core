from sereleum.data.stores.postgres.cluster_crossrefs_store import PostgresClusterCrossRefStore
from domains.articles.models import ArticleClusterCrossRefModel
from domains.articles.mappers import ArticleClusterCrossRefMapper

class ArticleClusterCrossRefStore( PostgresClusterCrossRefStore[ArticleClusterCrossRefModel]):
    model = ArticleClusterCrossRefModel
    mapper = ArticleClusterCrossRefMapper()