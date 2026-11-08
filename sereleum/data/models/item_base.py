from sqlalchemy import Column, Text
from sereleum.data.models.base import Base

class ItemBase(Base):
    __abstract__ = True

    id = Column(Text, primary_key=True)
