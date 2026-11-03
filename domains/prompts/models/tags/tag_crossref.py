from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sereleum.data.models.tags.tag_crossref_base import TagCrossRefBase

class PromptTagCrossRefModel(TagCrossRefBase):
    __tablename__ = "prompt_tag_crossref"

    item_id = mapped_column(ForeignKey("prompts.id", ondelete="CASCADE"))
    tag_id = mapped_column(ForeignKey("prompt_tags.id", ondelete="CASCADE"))