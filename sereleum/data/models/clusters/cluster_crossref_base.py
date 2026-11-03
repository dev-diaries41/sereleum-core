from sqlalchemy import Column, Text
from sereleum.data.models.base import Base

class ClusterCrossRefBase(Base):
    __abstract__ = True

    item_id = Column(Text, primary_key=True)
    cluster_id = Column(Text, nullable=False, index=True)