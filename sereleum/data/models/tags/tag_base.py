from sqlalchemy import Column, Text, Integer
from sereleum.data.models.base import Base

class TagBase(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)    
    name = Column(Text, nullable=False, index=True, unique=True)
