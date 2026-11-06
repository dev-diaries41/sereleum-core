from sqlalchemy import Text, Integer
from sereleum.data.models.base import Base
from sqlalchemy.orm import mapped_column


class TagCrossRefBase(Base):
    __abstract__ = True

    item_id = mapped_column(Text, primary_key=True)
    tag_id = mapped_column(Integer, primary_key=True)