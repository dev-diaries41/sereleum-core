import os
import json

from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Request, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from sse_starlette import EventSourceResponse

from typing import Optional
from tempfile import NamedTemporaryFile

from api.redis import redis_client
from api.prompts.tasks import index_prompts_task
from api.prompts.helpers import get_prompts_overview

from smartscan.models.model_manager import ModelManager

from llm_connect.schemas.llm import LLMProviderConfig
from llm_connect.providers.openai import OpenAIProvider

from sereleum.constants.db import POSTGRES_DSN
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.constants import  UPLOAD_DIR
from sereleum.constants.api import Routes

from api.schemas.response import FailMessage, CompleteMessage, ProgressMessage, ActiveMessage
from api.schemas.request import (
    GetItemsRequest, 
    GetItemsByIdRequest,
    QueryItemsRequest, 
    MergeClustersRequest,
    )
from api.schemas.response import (
    GetItemsResponse, 
    GetCountResponse, 
    GetClustersResponse, 
    GetPromptsOverviewResponse, 
    RenameClusterResponse, 
    MoveItemResponse, 
    AddItemsResponse,
    MergeResponse
    )
from sereleum.errors import SereleumError, ErrorCode
from sereleum.schemas.cluster import ClusterCrossRefFilter, ClusterFilter
from sereleum.schemas.item import BaseItemFilter

from domains.prompts.prompt import Prompt
from sereleum.clusters.plot import  get_cluster_plot
from sereleum.clusters.helpers import get_prompt_cluster_manager
from sereleum.data.helpers import create_sessionmaker
from sereleum.helpers import get_index_progres_key, get_index_status_key, get_cluster_status_key, get_cluster_status_channel, get_index_progress_channel

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

model_manager = ModelManager()
text_embedder = model_manager.get_text_embedder("all-distilroberta-v1")
text_embedder.init()
llm = OpenAIProvider(OPENAI_API_KEY, LLMProviderConfig(model=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))

sessionmaker = create_sessionmaker(POSTGRES_DSN)

cluster_manager = get_prompt_cluster_manager(sessionmaker, embed_dim=text_embedder.embedding_dim, llm=llm)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_methods=["POST", "OPTIONS", "GET", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)

os.makedirs(UPLOAD_DIR, exist_ok=True)

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


@app.post(Routes.INDEX_FILE_ENDPOINT) 
async def index_items(file: UploadFile = File(...), auto_label: bool = Form(False), default_threshold: float = Form(0.3)):
    with NamedTemporaryFile(dir=UPLOAD_DIR, delete=False, suffix=".json") as tmp:
        tmp.write(await file.read())
        tmp.flush()
    job = index_prompts_task.send(tmp.name, auto_label, default_threshold)
    return AddItemsResponse(status='queued', job_id=job.message_id )

@app.post(Routes.BASE_ITEMS_ENDPOINT)
async def get_items(req: GetItemsRequest):
    query_filter = BaseItemFilter(cluster_ids=req.cluster_ids) if req.cluster_ids else None
    items = await cluster_manager.item_store.get(filter=query_filter, limit=req.limit, offset=req.offset)
    return JSONResponse(GetItemsResponse[Prompt](items=items).model_dump(mode="json"))

@app.post(Routes.GET_ITEMS_BY_IDS_ENDPOINT)
async def get_items_by_id(req: GetItemsByIdRequest):
    items = await cluster_manager.item_store.get(filter=BaseItemFilter(ids=req.item_ids))
    return JSONResponse(GetItemsResponse[Prompt](items=items).model_dump(mode="json"))

@app.post(Routes.QUERY_ITEMS_ENDPOINT)
async def query_items(req: QueryItemsRequest):
    embedding = text_embedder.embed(req.query)[0]
    ids = None
    if req.cluster_ids:
        crossrefs = await cluster_manager.crossrefs_store.get(filter=ClusterCrossRefFilter(include_cluster_ids=req.cluster_ids))
        ids = [c.item_id for c in crossrefs]
    query_result = await cluster_manager.item_embedding_store.query(embedding, topK=req.limit, ids=ids)
    items = await cluster_manager.item_store.get(filter=BaseItemFilter(ids=query_result.ids))
    return JSONResponse(GetItemsResponse[Prompt](items=items).model_dump(mode="json"))


@app.get(Routes.COUNT_ITEMS_ENDPOINT)
async def count_items():
    count = await cluster_manager.item_store.count()
    return JSONResponse(GetCountResponse(count=count).model_dump())


@app.patch(Routes.BASE_ITEMS_ENDPOINT)
async def move_item_route(item_id: str, cluster_id: str):
    try:
        await  cluster_manager.assign({item_id : cluster_id})
    except SereleumError as e:
        if e.code == ErrorCode.INVALID_ARGUMENT:
            raise HTTPException(status_code=400, detail="Prompt or cluster id doesnt exist")
        else:
            raise e
    return JSONResponse(MoveItemResponse(updated_cluster_id=cluster_id).model_dump())


@app.get(Routes.BASE_CLUSTER_ENDPOINT)
async def get_cluster(cluster_id: Optional[str] = None, limit: Optional[str] = None, offset: Optional[str] = None):
    limit_int = int(limit) if limit not in (None, "") else None
    offset_int = int(offset) if offset not in (None, "") else None
    if not cluster_id :
        clusters_orm = await cluster_manager.cluster_store.get(limit=limit_int, offset=offset_int)
    else:
        clusters_orm = await cluster_manager.cluster_store.get(filter=ClusterFilter(ids=[cluster_id]))
    clusters = cluster_manager.from_cluster_orm_list(clusters_orm)
    return JSONResponse(GetClustersResponse(clusters=clusters).model_dump())


@app.patch(Routes.BASE_CLUSTER_ENDPOINT)
async def rename_cluster(cluster_id: str, label: str):
    updated = await cluster_manager.update_label(cluster_id, label)
    if not updated:
        raise HTTPException(status_code=404, detail="Label doesn't exist")

    return JSONResponse(RenameClusterResponse(updated_label=label).model_dump())


@app.get(Routes.COUNT_CLUSTERS_ENDPOINT)
async def count_clusters():
    count = await cluster_manager.cluster_store.count()
    return JSONResponse(GetCountResponse(count=count).model_dump())

@app.get(Routes.GET_CLUSTER_PLOT_ENDPOINT)
async def get_clusters_plot_route():
    img_bytes = await get_cluster_plot(cluster_manager)
    return Response(status_code=200 if img_bytes else 204, content=img_bytes, media_type="image/png")


@app.post(Routes.MERGE_CLUSTERS_ENDPOINT)
async def merge_clusters_route(req: MergeClustersRequest):
    if not req.merges:
        raise HTTPException(status_code=400, detail="Merges cannot be empty")
    updated_clusters = await cluster_manager.merge(req.merges)
    return JSONResponse(MergeResponse(updated_clusters=updated_clusters).model_dump())


@app.get(Routes.GET_PROMPTS_OVERVIEW_ENDPOINT)
async def get_overview():
    overview = await get_prompts_overview(cluster_manager)
    return JSONResponse(GetPromptsOverviewResponse(**overview.model_dump()).model_dump())
