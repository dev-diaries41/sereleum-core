from revelium.schemas.llm import LLMClientConfig
from revelium.prompts.prompts_manager import PromptsManager
from revelium.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from revelium.constants import DEFAULT_CHROMADB_PATH
from revelium.models.manage import ModelManager
from revelium.embeddings.helpers import get_embedding_store
from revelium.prompts.indexer import PromptIndexer
from revelium.prompts.indexer_listener import PromptIndexListener
from revelium.providers.llm.openai import OpenAIClient

model_manager = ModelManager()
text_embedder = model_manager.get_text_embedder('all-minilm-l6-v2')
text_embedder.init()
