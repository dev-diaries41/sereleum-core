import os
import asyncio

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

from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.constants import  UPLOAD_DIR
from sereleum.constants.api import Routes
from sereleum.schemas.api import FailMessage, CompleteMessage, ProgressMessage
from sereleum.errors import SereleumError, ErrorCode
from sereleum.schemas.api import (
    GetPromptsRequest, 
    GetPromptsByIdsRequest,
    GetPromptsResponse, 
    GetCountResponse, 
    GetClustersResponse, 
    GetPromptsOverviewResponse, 
    UpdateLabelResponse, 
    QueryPromptsRequest, 
    UpdatePromptClusterIdResponse, 
    AddPromptsResponse,
    MergeClustersRequest,
    MergeResponse
    )
from sereleum.data.db_config import get_config
from sereleum.clusters.plot import  get_cluster_plot
from sereleum.clusters.helpers import get_prompt_cluster_manager
from sereleum.schemas.cluster import ClusterCrossRefFilter
from sereleum.schemas.items.prompt import PromptFilter

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

model_manager = ModelManager()
text_embedder = model_manager.get_text_embedder("all-distilroberta-v1")
text_embedder.init()
llm = OpenAIProvider(OPENAI_API_KEY, LLMProviderConfig(model=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
db_config = get_config()
cluster_manager = get_prompt_cluster_manager(db_config, embed_dim=text_embedder.embedding_dim, llm=llm)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_methods=["POST", "OPTIONS", "GET", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)

os.makedirs(UPLOAD_DIR, exist_ok=True)



@app.get(Routes.SSE_PROMPTS_INDEX_PROGRESS)
async def track_prompts_index_progress(request: Request, job_id: str | None = None):
    if not job_id:
        return EventSourceResponse(
            [{"event": "failed", "data": FailMessage(error="invalid job id").model_dump_json()}],
            status_code=400,
        )

    async def event_generator():
        sent_active_msg = False
        try:
            while True:
                if await request.is_disconnected():
                    break

                progress = redis_client.get(f"progress_{job_id}")
                status = redis_client.get(f"status_{job_id}")

                if status == 'active':
                    if not sent_active_msg:
                        yield {"event": "active", "data": {}}
                        sent_active_msg = True

                if status == 'failed':
                    raise RuntimeError("Job failed")

                if progress:
                    if float(progress) == 1 or status == 'complete':
                        yield {"event": "progress", "data": ProgressMessage(progress=float(progress)).model_dump_json()}
                        yield {"event": "complete", "data": {}}
                        break
                    yield {"event": "progress", "data": ProgressMessage(progress=float(progress)).model_dump_json()}
                await asyncio.sleep(0.5)
        except RuntimeError:
            yield {"event": "failed", "data": FailMessage(error="error indexing prompts").model_dump_json()}
            return

    return EventSourceResponse(event_generator())


@app.get(Routes.SSE_PROMPTS_CLUSTER_STATUS)
async def track_prompts_cluster_status(request: Request, job_id: str | None = None):
    if not job_id:
        return EventSourceResponse(
            [{"event": "failed", "data": FailMessage(error="invalid job id").model_dump_json()}],
            status_code=400,
        )

    async def event_generator():
        sent_active_msg = False
        try:
            while True:
                if await request.is_disconnected():
                    break

                status = redis_client.get(f"{job_id}")

                if status == 'active':
                    if not sent_active_msg:
                        yield {"event": "active", "data": {}}
                        sent_active_msg = True

                if status == 'failed':
                    raise RuntimeError("Job failed")

                if status == 'complete':
                    yield {"event": "complete", "data": {}}
                    break
                await asyncio.sleep(0.5)
        except RuntimeError:
            yield {"event": "failed", "data": FailMessage(error="error clustering prompts").model_dump_json()}
            return

    return EventSourceResponse(event_generator())

@app.post(Routes.ADD_PROMPTS_FILE_ENDPOINT) 
async def add_prompts_file(file: UploadFile = File(...), auto_label: bool = Form(False), default_threshold: float = Form(0.3)):
    with NamedTemporaryFile(dir=UPLOAD_DIR, delete=False, suffix=".json") as tmp:
        tmp.write(await file.read())
        tmp.flush()
        job = index_prompts_task.send(tmp.name, auto_label, default_threshold)
    return AddPromptsResponse(status='queued', job_id=job.message_id )

@app.post(Routes.BASE_PROMPTS_ENDPOINT)
async def get_prompts(req: GetPromptsRequest):
    query_filter = PromptFilter(cluster_ids=req.cluster_ids) if req.cluster_ids else None
    prompts = await cluster_manager.item_store.get(filter=query_filter, limit=req.limit, offset=req.offset)
    return JSONResponse(GetPromptsResponse(prompts=prompts).model_dump())


@app.post(Routes.GET_PROMPTS_BY_IDS_ENDPOINT)
async def get_prompts_by_ids(req: GetPromptsByIdsRequest):
    prompts = await cluster_manager.item_store.get_by_ids(req.prompt_ids)
    return JSONResponse(GetPromptsResponse(prompts=prompts).model_dump())

@app.post(Routes.QUERY_PROMPTS_ENDPOINT)
async def query_prompts(req: QueryPromptsRequest):
    embedding = text_embedder.embed(req.query)
    ids = None
    if req.cluster_ids:
        crossrefs = await cluster_manager.crossrefs_store.get(filter=ClusterCrossRefFilter(include_cluster_ids=req.cluster_ids))
        ids = [c.item_id for c in crossrefs]
    query_result = await cluster_manager.item_embedding_store.query(embedding, topK=req.limit, ids=ids)
    prompts = await cluster_manager.item_store.get_by_ids(query_result.ids)
    return JSONResponse(GetPromptsResponse(prompts=prompts).model_dump())


@app.get(Routes.COUNT_PROMPTS_ENDPOINT)
async def count_prompts():
    count = await cluster_manager.item_store.count()
    return JSONResponse(GetCountResponse(count=count).model_dump())


@app.get(Routes.GET_PROMPTS_OVERVIEW_ENDPOINT)
async def get_overview():
    overview = await get_prompts_overview(cluster_manager)
    return JSONResponse(GetPromptsOverviewResponse(**overview.model_dump()).model_dump())


@app.patch(Routes.BASE_PROMPTS_ENDPOINT)
async def update_prompt_cluster(prompt_id: str, cluster_id: str):
    try:
        await  cluster_manager.assign({prompt_id : cluster_id})
    except SereleumError as e:
        if e.code == ErrorCode.ITEM_NOT_FOUND:
            raise HTTPException(status_code=404, detail="Prompt not found")
        else:
            raise e
    return JSONResponse(UpdatePromptClusterIdResponse(updated_cluster_id=cluster_id).model_dump())




@app.get(Routes.BASE_CLUSTER_ENDPOINT)
async def get_clusters(cluster_id: Optional[str] = None, limit: Optional[str] = None, offset: Optional[str] = None):
    limit_int = int(limit) if limit not in (None, "") else None
    offset_int = int(offset) if offset not in (None, "") else None
    if not cluster_id :
        clusters = await cluster_manager.cluster_store.get(limit=limit_int, offset=offset_int)
    else:
        clusters = await cluster_manager.cluster_store.get_by_ids([cluster_id])

    return JSONResponse(GetClustersResponse(clusters=clusters).model_dump())


@app.patch(Routes.BASE_CLUSTER_ENDPOINT)
async def update_cluster_label(cluster_id: str, label: str):
    updated = await cluster_manager.update_label(cluster_id, label)
    if not updated:
        raise HTTPException(status_code=404, detail="Label doesn't exist")

    return JSONResponse(UpdateLabelResponse(updated_label=label).model_dump())


@app.get(Routes.COUNT_CLUSTERS_ENDPOINT)
async def count_clusters():
    count = await cluster_manager.cluster_store.count()
    return JSONResponse(GetCountResponse(count=count).model_dump())

@app.get(Routes.GET_CLUSTER_PLOT_ENDPOINT)
async def get_clusters_plot():
    img_bytes = await get_cluster_plot(cluster_manager)
    return Response(status_code=200 if img_bytes else 204, content=img_bytes, media_type="image/png")


@app.post(Routes.MERGE_CLUSTERS_ENDPOINT)
async def merge_clusters(req: MergeClustersRequest):
    if not req.merges:
        raise HTTPException(status_code=400, detail="Merges cannot be empty")
    updated_clusters = await cluster_manager.merge(req.merges)
    return JSONResponse(MergeResponse(updated_clusters=updated_clusters).model_dump())
