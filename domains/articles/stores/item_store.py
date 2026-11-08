from sqlalchemy import exists, select

from sereleum.data.types import Filter
from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore

from domains.articles.models import ArticleModel, ArticleClusterCrossRefModel, ArticleTagCrossRefModel
from domains.articles.item import Article
from domains.articles.mappers import ArticleMapper


class ArticleStore(BasePostgresStore[ArticleModel, Article]):
    model = ArticleModel
    mapper = ArticleMapper()

    def apply_filters(self, stmt, f: Filter | None):
        if not f:
            return stmt

        if (ids := f.get('ids')) is not None:
                stmt = stmt.where(self.model.id.in_(ids))
        
        if (cluster_ids := f.get('cluster_ids')) is not None:
            stmt = stmt.where(
                exists(
                    select(1).where(
                        ArticleClusterCrossRefModel.item_id == self.model.id,
                        ArticleClusterCrossRefModel.cluster_id.in_(cluster_ids),
                    )
                )
            )

        if (tag_ids := f.get('tag_ids')) is not None:
                    stmt = stmt.where(
                        exists(
                            select(1).where(
                                ArticleTagCrossRefModel.item_id == self.model.id,
                                ArticleTagCrossRefModel.tag_id.in_(tag_ids),
                            )
                        )
                    )
        
        if (published_after := f.get('published_after')) is not None:
            stmt = stmt.where(self.model.published >= published_after)
        
        if (published_before := f.get('published_before')) is not None:
            stmt = stmt.where(self.model.published <= published_before)
        

        return stmt
    