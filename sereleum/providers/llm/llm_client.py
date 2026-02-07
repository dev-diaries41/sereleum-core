from abc import abstractmethod, ABC
from typing import List, Optional, Dict, TypeVar, Type
from pydantic import BaseModel
from sereleum.schemas.llm import Message
import numpy as np

JsonOutput = TypeVar("JsonOutput", bound=BaseModel)

class LLMClient(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, history: Optional[List[Message]] = None) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def generate_json(self, prompt: str, format: Type[JsonOutput], images: Optional[List[Dict[str, str]]] = None, history: Optional[List[Message]] = None) -> JsonOutput: 
        raise NotImplementedError
    
    @abstractmethod
    def generate_text_from_images(self, prompt: str, images: List[Dict[str, str]], history: Optional[List[Message]] = None) -> str:
        raise NotImplementedError
