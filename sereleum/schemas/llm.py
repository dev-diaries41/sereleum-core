from smartscan import ClassificationResult
from pydantic import BaseModel

class LLMClassificationResult(ClassificationResult):
    confidence: float

class BatchLLMClassificationResult(BaseModel):
    results: list[LLMClassificationResult]