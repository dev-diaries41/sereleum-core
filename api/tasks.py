import os
import json
import dramatiq
import redis

from dramatiq.middleware import AsyncIO, CurrentMessage
from dramatiq.brokers.redis import RedisBroker

from revelium.types import Prompt
from revelium.embeddings.helpers import get_embedding_store
from revelium.index.indexer import PromptIndexer
from revelium.index.indexer_listener import PromptIndexListener
from revelium.providers.llm.openai import OpenAIClient
from revelium.models.manage import ModelManager
from revelium.schemas.llm import LLMClientConfig
from revelium.prompts_manager import PromptsManager
from revelium.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from revelium.constants import DEFAULT_CHROMADB_PATH

from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

redis_client=redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    db=2
)

redis_broker = RedisBroker(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
)

redis_broker.add_middleware(AsyncIO())
redis_broker.add_middleware(CurrentMessage())
dramatiq.set_broker(redis_broker)

model_manager = ModelManager()
text_embedder = model_manager.get_text_embedder('all-minilm-l6-v2')
text_embedder.init()

@dramatiq.actor
async def index_prompts(file_path: str):
    msg = CurrentMessage().get_current_message()
    with open(file_path) as f:
        prompts = [Prompt(**p) for p in json.load(f)]
    prompt_embedding_store = get_embedding_store(DEFAULT_CHROMADB_PATH, PromptsManager.PROMPT_TYPE, 'all-minilm-l6-v2', text_embedder.embedding_dim) 
    cluster_embedding_store = get_embedding_store(DEFAULT_CHROMADB_PATH, PromptsManager.CLUSTER_TYPE, 'all-minilm-l6-v2', text_embedder.embedding_dim) 
    llm = OpenAIClient(OPENAI_API_KEY, LLMClientConfig(model_name=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
    prompts_manager = PromptsManager(llm_client=llm, prompt_embedding_store=prompt_embedding_store, cluster_embedding_store=cluster_embedding_store)
    indexer = PromptIndexer(text_embedder, prompt_embedding_store, listener=PromptIndexListener(prompts_manager, msg.message_id, redis_client))
    await indexer.run(prompts)
