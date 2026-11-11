from dramatiq import Actor

from typing import Type

from fastapi import  UploadFile, File, Form, APIRouter
from fastapi.concurrency import run_in_threadpool

from tempfile import NamedTemporaryFile

from api.routers.routes import Routes
from api.schemas.request import GetItemsRequest, GetItemsByIdRequest, QueryItemsRequest
from api.schemas.response import GetItemsResponse, GetCountResponse, AddItemsResponse
from smartscan.types import TextEmbeddingProvider

from sereleum.data.types import TItem
from sereleum.data.stores.item_embed_store import ItemEmbedStore
from sereleum.constants import  UPLOAD_DIR


def create_items_router(
        item_type: Type[TItem], 
        item_embed_store: ItemEmbedStore[TItem], 
        text_embedder: TextEmbeddingProvider,
        index_worker: Actor
        ) -> APIRouter:
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
        query_filter = {
            'cluster_ids': req.cluster_ids,
            'tag_ids': req.tag_ids
        }
   
        items = await item_embed_store.items.get(filter=query_filter, limit=req.limit, offset=req.offset)
        return GetItemsResponse[item_type](items=items)

    @router.post(Routes.GET_ITEMS_BY_IDS_ENDPOINT, response_model=GetItemsResponse[item_type])
    async def get_items_by_id(req: GetItemsByIdRequest):
        items = await item_embed_store.items.get(filter={'ids': req.item_ids})
        return GetItemsResponse[item_type](items=items)

    @router.post(Routes.QUERY_ITEMS_ENDPOINT, response_model=GetItemsResponse[item_type])
    async def query_items(req: QueryItemsRequest):
        embedding = (await run_in_threadpool(text_embedder.embed, req.query))[0]

        ids = None
        if req.cluster_ids:
            ids = await item_embed_store.items.get_ids(filter={'cluster_ids': req.cluster_ids})
        query_result = await item_embed_store.embeds.query(embedding, topK=req.limit, ids=ids)
        items = await item_embed_store.items.get(filter={'ids': query_result.ids})
        return GetItemsResponse[item_type](items=items)

    @router.get(Routes.COUNT_ITEMS_ENDPOINT, response_model=GetCountResponse)
    async def count_items():
        count = await item_embed_store.items.count()
        return GetCountResponse(count=count)

    
    return router