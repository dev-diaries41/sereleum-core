from sqlalchemy import Column, Text, Integer, Float
from sereleum.data.base import Base

class PromptClusterModel(Base):
    __tablename__ = "prompt_clusters"

    id = Column(Text, primary_key=True)
    prototype_size = Column(Integer, nullable=False)
    label = Column(Text, nullable=False)
    mean_similarity = Column(Float, nullable=False)
    std_similarity = Column(Float, nullable=False)