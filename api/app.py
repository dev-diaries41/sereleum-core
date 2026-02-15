import os
import asyncio

from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Request, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi import Request
from sse_starlette import EventSourceResponse

from typing import Optional
from tempfile import NamedTemporaryFile

from api.tasks import index_prompts_task
from api.redis import redis_client

from smartscan.models.model_manager import ModelManager

from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.constants import  UPLOAD_DIR
from sereleum.constants.api import Routes
from sereleum.cluster import  get_cluster_plot
from sereleum.schemas.llm import LLMClientConfig
from sereleum.schemas.api import FailMessage, CompleteMessage, ProgressMessage
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.clusters_manager import PromptClustersManager
from sereleum.prompts.helpers import get_prompts_overview
from sereleum.store.helpers import get_embedding_store
from sereleum.providers.llm.openai import OpenAIClient
from sereleum.errors import ReveliumError, ErrorCode
from sereleum.schemas.api import (
    GetPromptsRequest, 
    GetPromptsResponse, 
    GetCountResponse, 
    GetLabelsResponse, 
    GetClustersResponse, 
    GetPromptsOverviewResponse, 
    UpdateLabelResponse, 
    GetClustersAccuracyResponse, 
    QueryPromptsRequest, 
    UpdatePromptClusterIdResponse, 
    AddPromptsResponse,
    MergeClustersRequest,
    MergeResponse
    )

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_methods=["POST", "OPTIONS", "GET", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)


os.makedirs(UPLOAD_DIR, exist_ok=True)

model_manager = ModelManager()
text_embedder = model_manager.get_text_embedder('all-minilm-l6-v2')
text_embedder.init()
llm = OpenAIClient(OPENAI_API_KEY, LLMClientConfig(model_name=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))

# TODO: pass client id to get unique collections per client
def get_prompt_manager():
    prompt_embedding_store = get_embedding_store( 'prompt', 'all-minilm-l6-v2', text_embedder.embedding_dim) 
    return  PromptsManager(embedding_store=prompt_embedding_store)


def get_cluster_manager(prompt_manager: PromptsManager):
    cluster_embedding_store = get_embedding_store('cluster', 'all-minilm-l6-v2', text_embedder.embedding_dim) 
    return  PromptClustersManager(embedding_store=cluster_embedding_store, items_manager=prompt_manager, llm=llm)


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
async def add_prompts_file(file: UploadFile = File(...), auto_label: bool = Form(False), auto_merge_threshold: float = Form(0.9), initial_threshold: float = Form(0.3)):
    with NamedTemporaryFile(dir=UPLOAD_DIR, delete=False, suffix=".json") as tmp:
        tmp.write(await file.read())
        tmp.flush()
        job = index_prompts_task.send(tmp.name, auto_label, auto_merge_threshold, initial_threshold)
    return AddPromptsResponse(status='queued', job_id=job.message_id )

@app.post(Routes.BASE_PROMPTS_ENDPOINT)
async def get_prompts(req: GetPromptsRequest):
    if req.prompt_ids and req.limit:
        raise HTTPException(status_code=400, detail="Prompt ids and limit filtering must be used seperately")
    prompts_manager = get_prompt_manager()
    prompts = await run_in_threadpool(prompts_manager.get_prompts, req.prompt_ids, req.cluster_ids, req.limit, req.offset)
    return JSONResponse(GetPromptsResponse(prompts=prompts).model_dump())


@app.post(Routes.QUERY_PROMPTS_ENDPOINT)
async def query_prompts(req: QueryPromptsRequest):
    prompts_manager = get_prompt_manager()
    prompts = await run_in_threadpool(prompts_manager.query_prompts, text_embedder, req.query, req.cluster_ids, req.limit)
    return JSONResponse(GetPromptsResponse(prompts=prompts).model_dump())


@app.get(Routes.COUNT_PROMPTS_ENDPOINT)
async def count_prompts():
    prompts_manager = get_prompt_manager()
    count = await run_in_threadpool( prompts_manager.embedding_store.count)
    return JSONResponse(GetCountResponse(count=count).model_dump())


@app.get(Routes.GET_PROMPTS_OVERVIEW_ENDPOINT)
async def get_overview():
    prompts_manager = get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager)
    overview = await run_in_threadpool( get_prompts_overview, prompts_manager, clusters_manager)
    return JSONResponse(GetPromptsOverviewResponse(**overview.model_dump()).model_dump())


@app.patch(Routes.BASE_PROMPTS_ENDPOINT)
async def update_prompt_cluster(prompt_id: str, cluster_id: str):
    try:
        prompts_manager = get_prompt_manager()
        await run_in_threadpool( prompts_manager.update_prompt_cluster , prompt_id,  cluster_id)
    except ReveliumError as e:
        if e.code == ErrorCode.PROMPT_NOT_FOUND:
            raise HTTPException(status_code=404, detail="Prompt not found")
        else:
            raise e
    return JSONResponse(UpdatePromptClusterIdResponse(updated_cluster_id=cluster_id).model_dump())




@app.get(Routes.BASE_CLUSTER_ENDPOINT)
async def get_clusters(cluster_id: Optional[str] = None, limit: Optional[str] = None, offset: Optional[str] = None):
    limit_int = int(limit) if limit not in (None, "") else None
    offset_int = int(offset) if offset not in (None, "") else None
    prompts_manager = get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager)
    clusters = await run_in_threadpool(clusters_manager.get_clusters, cluster_id, limit_int, offset_int, ['metadatas'])
    return JSONResponse(GetClustersResponse(clusters=list(clusters.values())).model_dump())


@app.patch(Routes.BASE_CLUSTER_ENDPOINT)
async def update_cluster_label(cluster_id: str, label: str):
    prompts_manager = get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager)
    updated = await run_in_threadpool(
        clusters_manager.update_cluster_label, cluster_id, label
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Label doesn't exist")

    return JSONResponse(UpdateLabelResponse(updated_label=label).model_dump())


@app.get(Routes.COUNT_CLUSTERS_ENDPOINT)
async def count_clusters():
    prompts_manager = get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager)
    count = await run_in_threadpool( clusters_manager.embedding_store.count)
    return JSONResponse(GetCountResponse(count=count).model_dump())

@app.get(Routes.GET_CLUSTER_LABELS_ENDPOINT)
async def get_existing_labels():
    prompts_manager = get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager)
    labels = await run_in_threadpool(clusters_manager.get_existing_labels)
    return JSONResponse(GetLabelsResponse(labels=labels).model_dump())


@app.get(Routes.GET_CLUSTER_ACCURACY_ENDPOINT)
async def get_cluster_accuracy():
    prompts_manager = get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager)
    accuracy = await run_in_threadpool(clusters_manager.calculate_cluster_accuracy)
    return JSONResponse(GetClustersAccuracyResponse(accuracy=accuracy).model_dump())


@app.get(Routes.GET_CLUSTER_PLOT_ENDPOINT)
async def get_clusters_plot():
    prompts_manager = get_prompt_manager()
    img_bytes = await run_in_threadpool(get_cluster_plot, prompts_manager)
    return Response(status_code=200 if img_bytes else 204, content=img_bytes, media_type="image/png")


@app.post(Routes.MERGE_CLUSTERS_ENDPOINT)
async def merge_clusters(req: MergeClustersRequest):
    if not req.merges:
        raise HTTPException(status_code=400, detail="Merges cannot be empty")
    prompts_manager = get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager)
    updated_clusters = await run_in_threadpool(clusters_manager.merge_clusters,req.merges)
    return JSONResponse(MergeResponse(updated_clusters=updated_clusters).model_dump())
