from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sereleum.data.models.cluster_crossref_base import ClusterCrossRefBase

class ArticleClusterCrossRefModel(ClusterCrossRefBase):
    __tablename__ = "article_cluster_crossref"

    item_id = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    cluster_id = mapped_column(ForeignKey("article_clusters.id", ondelete="CASCADE"), nullable=False, index=True)