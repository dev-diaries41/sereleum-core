from typing import Type
from fastapi import  UploadFile, File, Form, APIRouter
from tempfile import NamedTemporaryFile

from api.routers.routes import Routes
from api.schemas.request import GetItemsRequest, GetItemsByIdRequest, QueryItemsRequest
from api.schemas.response import GetItemsResponse, GetCountResponse, AddItemsResponse, GetOverviewResponse
from api.workers.main import index_worker
from smartscan.types import TextEmbeddingProvider

from sereleum.data.types import TItem
from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.schemas.cluster import ClusterCrossRefFilter
from sereleum.schemas.item import BaseItemFilter
from sereleum.constants import  UPLOAD_DIR


def create_items_router(item_type: Type[TItem], cluster_manager: ClusterManager[TItem], text_embedder: TextEmbeddingProvider) -> APIRouter:
    router = APIRouter()

    @router.post(Routes.INDEX_FILE_ENDPOINT) 
    async def index_items(file: UploadFile = File(...), auto_label: bool = Form(False), default_threshold: float = Form(0.3)):
        with NamedTemporaryFile(dir=UPLOAD_DIR, delete=False, suffix=".json") as tmp:
            tmp.write(await file.read())
            tmp.flush()
        job = index_worker.send(tmp.name, auto_label, default_threshold)
        return AddItemsResponse(status='queued', job_id=job.message_id )

    @router.post(Routes.BASE_ITEMS_ENDPOINT, response_model=GetItemsResponse[item_type])
    async def get_items(req: GetItemsRequest):
        query_filter = BaseItemFilter(cluster_ids=req.cluster_ids) if req.cluster_ids else None
        items = await cluster_manager.item_store.get(filter=query_filter, limit=req.limit, offset=req.offset)
        return GetItemsResponse[item_type](items=items)

    @router.post(Routes.GET_ITEMS_BY_IDS_ENDPOINT, response_model=GetItemsResponse[item_type])
    async def get_items_by_id(req: GetItemsByIdRequest):
        items = await cluster_manager.item_store.get(filter=BaseItemFilter(ids=req.item_ids))
        return GetItemsResponse[item_type](items=items)

    @router.post(Routes.QUERY_ITEMS_ENDPOINT, response_model=GetItemsResponse[item_type])
    async def query_items(req: QueryItemsRequest):
        embedding = text_embedder.embed(req.query)[0]
        ids = None
        if req.cluster_ids:
            crossrefs = await cluster_manager.crossrefs_store.get(
                filter=ClusterCrossRefFilter(include_cluster_ids=req.cluster_ids)
            )
            ids = [c.item_id for c in crossrefs]
        query_result = await cluster_manager.item_embedding_store.query(embedding, topK=req.limit, ids=ids)
        items = await cluster_manager.item_store.get(filter=BaseItemFilter(ids=query_result.ids))
        return GetItemsResponse[item_type](items=items)

    @router.get(Routes.COUNT_ITEMS_ENDPOINT, response_model=GetCountResponse)
    async def count_items():
        count = await cluster_manager.item_store.count()
        return GetCountResponse(count=count)

    @router.get(Routes.GET_OVERVIEW_ENDPOINT, response_model=GetOverviewResponse)
    async def get_overview():
        overview = await cluster_manager.get_overview()
        return overview
    
    return router