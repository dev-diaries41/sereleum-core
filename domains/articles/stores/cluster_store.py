from sereleum.data.stores.postgres.cluster_store import PostgresClusterStore
from domains.articles.models import ArticleClusterModel, ArticleClusterCrossRefModel, ArticleModel
from domains.articles.models import ArticleModel, ArticleClusterCrossRefModel
from domains.articles.mappers import ArticleClusterMapper

class ArticleClusterStore(PostgresClusterStore[ArticleClusterModel, ArticleClusterCrossRefModel, ArticleModel]):
    model = ArticleClusterModel
    crossref_model = ArticleClusterCrossRefModel
    item_model = ArticleModel
    mapper = ArticleClusterMapper()