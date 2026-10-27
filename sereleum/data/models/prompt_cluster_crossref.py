from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sereleum.data.models.cluster_crossref_base import CrossRefBase

class PromptClusterCrossRefModel(CrossRefBase):
    __tablename__ = "prompts_cluster_crossref"

    item_id = mapped_column(ForeignKey("prompts.id", ondelete="CASCADE"), primary_key=True)
    cluster_id = mapped_column(ForeignKey("prompt_clusters.id", ondelete="CASCADE"), nullable=False, index=True)