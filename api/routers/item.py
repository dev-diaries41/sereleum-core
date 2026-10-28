from typing import Type
from fastapi import APIRouter

from api.schemas.request import GetItemsRequest, GetItemsByIdRequest, QueryItemsRequest
from api.schemas.response import GetItemsResponse, GetCountResponse
from sereleum.schemas.cluster import ClusterCrossRefFilter
from sereleum.schemas.item import BaseItemFilter
from smartscan.types import TextEmbeddingProvider
from sereleum.constants.api import Routes
from sereleum.data.types import TItem
from sereleum.clusters.cluster_manager import ClusterManager


def create_items_router(item_type: Type[TItem], cluster_manager: ClusterManager[TItem], text_embedder: TextEmbeddingProvider) -> APIRouter:
    router = APIRouter()

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

    return router