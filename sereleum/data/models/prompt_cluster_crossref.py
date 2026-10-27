from sqlalchemy import Column, Text, ForeignKey
from sereleum.data.base import Base

class PromptClusterCrossRefModel(Base):
    __tablename__ = "prompts_cluster_crossref"

    item_id = Column(
        Text,
        ForeignKey("prompts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    cluster_id = Column(
        Text,
        ForeignKey("prompt_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )