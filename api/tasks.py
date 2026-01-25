import json
import dramatiq
import os

from dramatiq.middleware import AsyncIO, CurrentMessage
from dramatiq.brokers.redis import RedisBroker

from sereleum.types import Prompt
from sereleum.embeddings.helpers import get_embedding_store
from sereleum.index.indexer import PromptIndexer
from sereleum.index.indexer_listener import PromptIndexListener
from sereleum.providers.llm.openai import OpenAIClient
from sereleum.models.manage import ModelManager
from sereleum.schemas.llm import LLMClientConfig
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.clusters_manager import ClustersManager
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.cluster import cluster_prompts

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
    return  ClustersManager(embedding_store=cluster_embedding_store, prompts_manager=prompt_manager, llm=llm)

@dramatiq.actor
async def index_prompts_task(file_path: str):
    try:
        msg = CurrentMessage().get_current_message()
        with open(file_path) as f:
            prompts = [Prompt(**p) for p in json.load(f)]
        prompt_embedding_store = get_embedding_store( 'prompt', 'all-minilm-l6-v2', text_embedder.embedding_dim) 
        indexer = PromptIndexer(text_embedder, prompt_embedding_store, listener=PromptIndexListener(msg.message_id, redis_client))
        await indexer.run(prompts)
        cluster_prompts_task.send()
    finally:
        os.remove(file_path)


# Note: in prod client_id will be passed instead of just using "cluster_job_status"
@dramatiq.actor
async def cluster_prompts_task():
    redis_client.set("cluster_job_status", "active", ex=86400)
    prompts_manager = get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager)
    await cluster_prompts(prompts_manager, clusters_manager, auto_label=False)
    redis_client.set("cluster_job_status", "complete", ex=86400)
