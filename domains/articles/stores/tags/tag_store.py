from sereleum.data.stores.postgres.tags.tag_store import PostgresTagStore
from domains.articles.models import ArticleTagModel, ArticleTagCrossRefModel, ArticleModel, ArticleClusterCrossRefModel
from domains.articles.mappers import ArticleTagMapper

class ArticleTagStore(PostgresTagStore[ArticleTagModel, ArticleTagCrossRefModel, ArticleModel]):
    model = ArticleTagModel
    tag_crossref_model = ArticleTagCrossRefModel
    cluster_crossref_model = ArticleClusterCrossRefModel
    item_model = ArticleModel
    mapper = ArticleTagMapper()