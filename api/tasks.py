import json
import dramatiq
import os
import chromadb

from dramatiq.middleware import AsyncIO, CurrentMessage
from dramatiq.brokers.redis import RedisBroker

from smartscan.models.model_manager import ModelManager

from sereleum.types import Prompt
from sereleum.prompts.indexer import PromptIndexer
from sereleum.prompts.indexer_listener import PromptIndexListener
from sereleum.providers.llm.openai import OpenAIClient
from sereleum.schemas.llm import LLMClientConfig
from sereleum.cluster import cluster_items
from sereleum.helpers import get_cluster_manager, get_prompt_manager
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL

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
text_embedder = model_manager.get_text_embedder("all-distilroberta-v1")
text_embedder.init()
llm = OpenAIClient(OPENAI_API_KEY, LLMClientConfig(model_name=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
client = chromadb.HttpClient(host='chromadb', port=8000, settings=chromadb.Settings(anonymized_telemetry=False))
prompts_manager = get_prompt_manager(client, "all-distilroberta-v1", text_embedder.embedding_dim)
clusters_manager = get_cluster_manager(client, "all-distilroberta-v1", text_embedder.embedding_dim, prompts_manager, llm)

@dramatiq.actor(max_retries = 2)
async def index_prompts_task(file_path: str, auto_label: bool = True, default_threshold: float = 0.55):
    try:
        msg = CurrentMessage().get_current_message()
        current_retries = msg.options.setdefault("retries", 0)

        if current_retries + 1 > 2:
            redis_client.set(f"status_{msg.message_id}", "failed", ex=86400)
            return
        
        with open(file_path) as f:
            prompts = [Prompt(**p) for p in json.load(f)]
        indexer = PromptIndexer(text_embedder, prompts_manager.embedding_store, listener=PromptIndexListener(msg.message_id, redis_client))
        await indexer.run(prompts)
        cluster_prompts_task.send(auto_label, default_threshold)
    finally:
        os.remove(file_path)


# Note: in prod client_id will be passed instead of just using "cluster_job_status"
@dramatiq.actor(max_retries = 2)
async def cluster_prompts_task(auto_label: bool = True, default_threshold: float = 0.3):
    msg = CurrentMessage().get_current_message()
    current_retries = msg.options.setdefault("retries", 0)

    if current_retries + 1 > 2:
        redis_client.set("cluster_job_status", "failed", ex=86400)
        return

    redis_client.set("cluster_job_status", "active", ex=86400)
    await cluster_items(prompts_manager, clusters_manager, auto_label=auto_label, default_threshold=default_threshold)
    redis_client.set("cluster_job_status", "complete", ex=86400)
