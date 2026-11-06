from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sereleum.data.models.tags.tag_crossref_base import TagCrossRefBase

class ArticleTagCrossRefModel(TagCrossRefBase):
    __tablename__ = "article_tag_crossref"

    item_id = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    tag_id = mapped_column(ForeignKey("article_tags.id", ondelete="CASCADE"), primary_key=True)