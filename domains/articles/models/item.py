from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from sereleum.data.models.item_base import ItemBase

class ArticleModel(ItemBase):
    __tablename__ = "articles"
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    published = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
