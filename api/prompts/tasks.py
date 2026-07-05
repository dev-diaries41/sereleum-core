import json
import dramatiq
import os

from dramatiq.middleware import AsyncIO, CurrentMessage

from smartscan.models.model_manager import ModelManager

from llm_connect.providers.openai import OpenAIProvider
from llm_connect.schemas.llm import LLMProviderConfig

from sereleum.schemas.items.prompt import Prompt
from sereleum.index.prompts.indexer import PromptIndexer
from sereleum.index.prompts.indexer_listener import PromptIndexListener
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.data.db_config import get_config
from sereleum.clusters.helpers import get_prompt_cluster_manager
from api.redis import redis_client, get_broker
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sereleum.logs import getLogger

redis_broker = get_broker()
redis_broker.add_middleware(AsyncIO())
redis_broker.add_middleware(CurrentMessage())
dramatiq.set_broker(redis_broker)

model_manager = ModelManager()
text_embedder = model_manager.get_text_embedder("all-distilroberta-v1")
text_embedder.init()
llm = OpenAIProvider(OPENAI_API_KEY, LLMProviderConfig(model=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
db_config = get_config()

engine = create_async_engine(db_config.dsn, echo=False)
sessionmaker = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

cluster_manager = get_prompt_cluster_manager(db_config, sessionmaker, embed_dim=text_embedder.embedding_dim, llm=llm)
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
@dramatiq.actor(max_retries = 2)
async def cluster_prompts_task(index_job_id: str, auto_label: bool = True, default_threshold: float = 0.3):
    msg = CurrentMessage().get_current_message()
    current_retries = msg.options.setdefault("retries", 0)
    cluster_status_key = cluster_job_key(index_job_id)

    if current_retries + 1 > 2:
        redis_client.set(cluster_status_key, "failed", ex=86400)
        logger.error(f"cluster job failed: {index_job_id}")
        return

    redis_client.set(cluster_status_key, "active", ex=86400)
    await cluster_manager.cluster(auto_label=auto_label, default_threshold=default_threshold)
    redis_client.set(cluster_status_key, "complete", ex=86400)


def cluster_job_key(index_job_id: str):
    return f"cluster_job_status_{index_job_id}"