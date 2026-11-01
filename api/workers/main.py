from smartscan.models.model_manager import ModelManager
from llm_connect.providers.openai import OpenAIProvider
from llm_connect.schemas.llm import LLMProviderConfig

from domains.prompts import create_cluster_manager, create_indexer
from sereleum.constants.db import POSTGRES_DSN
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.data.helpers import create_sessionmaker

from api.workers.register_workers import register_workers

model_manager = ModelManager()
text_embedder = model_manager.get_text_embedder('all_distilroberta_v1')
text_embedder.init()
llm = OpenAIProvider(
    OPENAI_API_KEY,
    LLMProviderConfig(
        model=DEFAULT_OPENAI_MODEL,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
    ),
)

sessionmaker = create_sessionmaker(POSTGRES_DSN)

cluster_manager = create_cluster_manager(sessionmaker, llm)
indexer = create_indexer(text_embedder, sessionmaker)

index_worker, cluster_worker = register_workers(indexer, cluster_manager)