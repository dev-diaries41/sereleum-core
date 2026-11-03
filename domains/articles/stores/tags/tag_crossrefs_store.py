from sereleum.data.stores.postgres.tags.tag_crossrefs_store import PostgresTagCrossRefStore
from domains.articles.models.tags.tag_crossref import ArticleTagCrossRefModel
from domains.articles.mappers import ArticleTagCrossRefMapper

class ArticleTagCrossRefStore( PostgresTagCrossRefStore[ArticleTagCrossRefModel]):
    model = ArticleTagCrossRefModel
    mapper = ArticleTagCrossRefMapper()