from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from openai.types import ResponsesModel
from smartscan import ClassificationResult

class LLMClientConfig(BaseModel):
    system_prompt: str
    model_name: str | ResponsesModel
    temperature: float = Field(default=0.1)
    max_output_tokens: int = Field(default=4000)
    stream: bool = Field(default=False)


class LLMClassificationResult(ClassificationResult):
    confidence: float
    
class Message(BaseModel):
    role: str
    content: Optional[str] = None

ImageDetail = Literal["low", "high", "auto"]

class ImageContent(BaseModel):
    type: str
    text: Optional[str] = None
    image_url: Optional[str] = None
    detail: Optional[ImageDetail] = None

class ImageMessage(BaseModel):
    role: str
    content: List[ImageContent]

