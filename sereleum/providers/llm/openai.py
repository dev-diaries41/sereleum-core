from typing import Optional, List, Type
from sereleum.providers.llm.llm_client import LLMClient
from openai import OpenAI
from sereleum.schemas.llm import LLMClientConfig, Message
from sereleum.providers.types import JsonOutput


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, config: LLMClientConfig):
        self.openai = OpenAI(api_key=api_key)
        self.config = config

    def generate_text(self, prompt: str, history: Optional[List[Message]] = None) -> str:
        response =  self.openai.responses.create(
        model=self.config.model_name,
        input = [
            Message(role="system", content=self.config.system_prompt),
            *(history or []),
            Message(role="user", content=prompt),
        ]
        )
        return response.output_text
    
    def generate_json(self, prompt:str, format: Type[JsonOutput], history: Optional[List[Message]] = None):
        response = self.openai.responses.parse(
            model=self.config.model_name,
            input=[
                    Message(role="system", content=self.config.system_prompt),
                    *(history or []),
                    Message(role="user", content=prompt),
            ],
            text_format=format,
        )
        return response.output_parsed

    #TODO
    def generate_text_from_images(self, prompt, images, history = None):
        pass