import json
import dramatiq
import os

from time import perf_counter

from dramatiq.middleware import AsyncIO, CurrentMessage

from smartscan.models.model_manager import ModelManager

from llm_connect.providers.openai import OpenAIProvider
from llm_connect.schemas.llm import LLMProviderConfig

from sereleum.schemas.items.prompt import Prompt
from sereleum.index.prompts.indexer import PromptIndexer
from sereleum.index.prompts.indexer_listener import PromptIndexListener
from sereleum.constants.db import POSTGRES_DSN
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.clusters.helpers import get_prompt_cluster_manager
from api.redis import redis_client, get_broker
from sereleum.logs import getLogger
from sereleum.helpers import get_cluster_status_key, get_cluster_status_channel
from sereleum.schemas.api import FailMessage, CompleteMessage, ActiveMessage
from sereleum.data.helpers import create_sessionmaker

redis_broker = get_broker()
redis_broker.add_middleware(AsyncIO())
redis_broker.add_middleware(CurrentMessage())
dramatiq.set_broker(redis_broker)

model_manager = ModelManager()
text_embedder = model_manager.get_text_embedder("all-distilroberta-v1")
text_embedder.init()
llm = OpenAIProvider(OPENAI_API_KEY, LLMProviderConfig(model=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
sessionmaker = create_sessionmaker(POSTGRES_DSN)

cluster_manager = get_prompt_cluster_manager(sessionmaker, embed_dim=text_embedder.embedding_dim, llm=llm)
logger = getLogger("tasks", "logs/tasks.log")

@dramatiq.actor(max_retries = 2)
async def index_prompts_task(file_path: str, auto_label: bool = True, default_threshold: float = 0.55):
    try:
        msg = CurrentMessage().get_current_message()
        current_retries = msg.options.setdefault("retries", 0)
        job_id = msg.message_id

        if current_retries + 1 > 2:
            redis_client.set(f"status_{job_id}", "failed", ex=86400)
            return
        
        with open(file_path) as f:
            prompts = [Prompt(**p) for p in json.load(f)]
        indexer = PromptIndexer(text_embedder, embeddings_store=cluster_manager.item_embedding_store, prompt_store=cluster_manager.item_store, listener=PromptIndexListener(msg.message_id, redis_client))
        await indexer.run(prompts)
        
        cluster_prompts_task.send(
            index_job_id=job_id,
            auto_label=auto_label,
            default_threshold=default_threshold,
        )

    finally:
        os.remove(file_path)


# Note: in prod client_id will be passed instead of just using "cluster_job_status"
@dramatiq.actor(max_retries=2)
async def cluster_prompts_task(index_job_id: str, auto_label: bool = True,default_threshold: float = 0.3):
    msg = CurrentMessage().get_current_message()
    current_retries = msg.options.setdefault("retries", 0)

    status_key = get_cluster_status_key(index_job_id)
    channel = get_cluster_status_channel(index_job_id)

    if current_retries + 1 > 2:
        await redis_client.set(status_key, "failed", ex=86400)
        await redis_client.publish(channel, FailMessage(error="cluster job failed").model_dump_json())
        logger.error(f"cluster job failed: {index_job_id}")
        return

    await redis_client.set(status_key, "active", ex=86400)
    await redis_client.publish(channel,ActiveMessage().model_dump_json())

    start = perf_counter()
    result = await cluster_manager.cluster(
        auto_label=auto_label,
        default_threshold=default_threshold
    )
    end = perf_counter()


    await redis_client.set(status_key, "complete", ex=86400)
    await redis_client.publish(
        channel,
        CompleteMessage(total_processed=len(result.assignments), time_elapsed=end-start).model_dump_json()
    )