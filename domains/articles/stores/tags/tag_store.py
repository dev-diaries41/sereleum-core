from sereleum.data.stores.postgres.tags.tag_store import PostgresTagStore
from domains.articles.models import ArticleTagModel, ArticleTagCrossRefModel, ArticleModel
from domains.articles.mappers import ArticleTagMapper

class ArticleTagStore(PostgresTagStore[ArticleTagModel, ArticleTagCrossRefModel, ArticleModel]):
    model = ArticleTagModel
    crossref_model = ArticleTagCrossRefModel
    item_model = ArticleModel
    mapper = ArticleTagMapper()