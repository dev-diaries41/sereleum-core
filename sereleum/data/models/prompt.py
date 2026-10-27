from sqlalchemy import Column, Text, Integer
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from sereleum.data.models.base import Base

class PromptModel(Base):
    __tablename__ = "prompts"

    id = Column(Text, primary_key=True)
    content = Column(Text, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    tokens = Column(Integer)