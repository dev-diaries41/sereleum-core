import json
import dramatiq
import os

from dramatiq.middleware import AsyncIO, CurrentMessage
from dramatiq.brokers.redis import RedisBroker

from smartscan.models.model_manager import ModelManager

from sereleum.types import Prompt
from sereleum.store.helpers import get_embedding_store
from sereleum.prompts.indexer import PromptIndexer
from sereleum.prompts.indexer_listener import PromptIndexListener
from sereleum.providers.llm.openai import OpenAIClient
from sereleum.schemas.llm import LLMClientConfig
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.clusters_manager import PromptClustersManager
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.cluster import cluster_items

from api.redis import REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, redis_client

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
llm = OpenAIClient(OPENAI_API_KEY, LLMClientConfig(model_name=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))


def get_prompt_manager():
    prompt_embedding_store = get_embedding_store( 'prompt', 'all-minilm-l6-v2', text_embedder.embedding_dim) 
    return  PromptsManager(embedding_store=prompt_embedding_store)


def get_cluster_manager(prompt_manager: PromptsManager):
    cluster_embedding_store = get_embedding_store('cluster', 'all-minilm-l6-v2', text_embedder.embedding_dim) 
    return  PromptClustersManager(embedding_store=cluster_embedding_store, items_manager=prompt_manager, llm=llm)

@dramatiq.actor(max_retries = 2)
async def index_prompts_task(file_path: str, auto_label: bool = True, initial_threshold: float = 0.55):
    try:
        msg = CurrentMessage().get_current_message()
        current_retries = msg.options.setdefault("retries", 0)

        if current_retries + 1 > 2:
            redis_client.set(f"status_{msg.message_id}", "failed", ex=86400)
            return
        
        with open(file_path) as f:
            prompts = [Prompt(**p) for p in json.load(f)]
        prompt_embedding_store = get_embedding_store( 'prompt', 'all-minilm-l6-v2', text_embedder.embedding_dim) 
        indexer = PromptIndexer(text_embedder, prompt_embedding_store, listener=PromptIndexListener(msg.message_id, redis_client))
        await indexer.run(prompts)
        cluster_prompts_task.send(auto_label, initial_threshold)
    finally:
        os.remove(file_path)


# Note: in prod client_id will be passed instead of just using "cluster_job_status"
@dramatiq.actor(max_retries = 2)
async def cluster_prompts_task(auto_label: bool = True, initial_threshold: float = 0.3):
    msg = CurrentMessage().get_current_message()
    current_retries = msg.options.setdefault("retries", 0)

    if current_retries + 1 > 2:
        redis_client.set("cluster_job_status", "failed", ex=86400)
        return

    redis_client.set("cluster_job_status", "active", ex=86400)
    prompts_manager = get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager)
    await cluster_items(prompts_manager, clusters_manager, auto_label=auto_label, initial_threshold=initial_threshold)
    redis_client.set("cluster_job_status", "complete", ex=86400)
