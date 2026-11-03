from sqlalchemy import Column, Text, Integer
from sereleum.data.models.base import Base

class TagCrossRefBase(Base):
    __abstract__ = True

    item_id = Column(Text, primary_key=True)
    tag_id = Column(Integer, primary_key=True)