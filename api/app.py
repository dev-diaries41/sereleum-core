import os
import json

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from sse_starlette import EventSourceResponse

from api.redis import redis_client
from api.prompts.helpers import get_prompts_overview

from smartscan.models.model_manager import ModelManager

from llm_connect.schemas.llm import LLMProviderConfig
from llm_connect.providers.openai import OpenAIProvider

from sereleum.constants.db import POSTGRES_DSN
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.constants import  UPLOAD_DIR
from sereleum.constants.api import Routes

from api.schemas.response import FailMessage, CompleteMessage, ProgressMessage, ActiveMessage
from api.schemas.response import GetPromptsOverviewResponse

from domains.prompts.item import Prompt
from domains.prompts.cluster_manager import get_cluster_manager
from sereleum.data.helpers import create_sessionmaker
from sereleum.helpers import get_index_progres_key, get_index_status_key, get_cluster_status_key, get_cluster_status_channel, get_index_progress_channel
from api.routers.item import create_items_router
from api.routers.cluster import create_clusters_router

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

model_manager = ModelManager()
text_embedder = model_manager.get_text_embedder("all-distilroberta-v1")
text_embedder.init()
llm = OpenAIProvider(OPENAI_API_KEY, LLMProviderConfig(model=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))

sessionmaker = create_sessionmaker(POSTGRES_DSN)

cluster_manager = get_cluster_manager(sessionmaker, text_embedder.embedding_dim, llm)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_methods=["POST", "OPTIONS", "GET", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)

os.makedirs(UPLOAD_DIR, exist_ok=True)


app.include_router(
    create_items_router(
        item_type=Prompt,
        cluster_manager=cluster_manager,
        text_embedder=text_embedder,
    )
)
app.include_router(create_clusters_router(cluster_manager))


@app.get(Routes.SSE_INDEX_PROGRESS)
async def track_index_progress_route(request: Request, job_id: str):
    async def event_generator():
        pubsub = redis_client.pubsub()
        channel = get_index_progress_channel(job_id)

        progress = await redis_client.get(get_index_progres_key(job_id))
        status = await redis_client.get(get_index_status_key(job_id))

        if progress is not None:
            yield {"event": "progress", "data": ProgressMessage(progress=float(progress)).model_dump_json()}

        if status == "active":
            yield {"event": "active", "data": ActiveMessage().model_dump_json()}

        elif status == "failed":
            yield {"event": "failed", "data": FailMessage(error="error indexing prompts").model_dump_json()}
            return

        elif status == "complete":
            yield {"event": "complete", "data": CompleteMessage().model_dump_json()}
            return

        await pubsub.subscribe(channel)

        try:
            while True:
                if await request.is_disconnected():
                    break

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                if not message:
                    continue

                data = json.loads(message["data"])

                yield {
                    "event": data["event"],
                    "data": json.dumps(data)
                }

                if data["event"] in ("complete", "failed"):
                    break

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return EventSourceResponse(event_generator())

@app.get(Routes.SSE_CLUSTER_STATUS)
async def track_prompts_cluster_status(request: Request, job_id: str):

    async def event_generator():
        pubsub = redis_client.pubsub()
        channel = get_cluster_status_channel(job_id)

        status_key = get_cluster_status_key(job_id)
        status = await redis_client.get(status_key)

        if status == "active":
            yield {"event": "active", "data": ActiveMessage().model_dump_json()}

        elif status == "failed":
            yield {
                "event": "failed",
                "data": FailMessage(error="error clustering prompts").model_dump_json()
            }
            return

        elif status == "complete":
            yield {"event": "complete", "data": CompleteMessage().model_dump_json()}
            return

        await pubsub.subscribe(channel)

        try:
            while True:
                if await request.is_disconnected():
                    break

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                if not message:
                    continue

                data = json.loads(message["data"])

                yield {
                    "event": data["event"],
                    "data": message["data"]
                }

                if data["event"] in ("complete", "failed"):
                    break

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return EventSourceResponse(event_generator())



@app.get(Routes.GET_PROMPTS_OVERVIEW_ENDPOINT, response_model=GetPromptsOverviewResponse)
async def get_overview():
    overview = await get_prompts_overview(cluster_manager)
    return GetPromptsOverviewResponse(**overview.model_dump())