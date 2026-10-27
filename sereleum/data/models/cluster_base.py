from sqlalchemy import Column, Text, Integer, Float
from sereleum.data.models.base import Base

class ClusterBase(Base):
    __abstract__ = True

    id = Column(Text, primary_key=True)
    prototype_size = Column(Integer, nullable=False)
    label = Column(Text, nullable=False)
    mean_similarity = Column(Float, nullable=False)
    std_similarity = Column(Float, nullable=False)