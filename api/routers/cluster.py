from typing import Optional

from fastapi import APIRouter, HTTPException, Response

from api.schemas.request import MergeRequest
from api.schemas.response import (
    GetCountResponse,
    GetCollectionsResponse,
    MergeResponse,
)
from sereleum.errors import SereleumError, ErrorCode
from sereleum.clusters.plot import get_cluster_plot
from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.data.types import TItem
from api.routers.routes import Routes


def create_clusters_router(cluster_manager: ClusterManager[TItem]) -> APIRouter:
    router = APIRouter()

    @router.patch(Routes.BASE_ITEMS_ENDPOINT,  status_code=204)
    async def move_items(item_ids: list[str], cluster_id: str):
        try:
            await cluster_manager.move(set(item_ids), cluster_id)
        except SereleumError as e:
            if e.code == ErrorCode.INVALID_ARGUMENT:
                raise HTTPException(status_code=400, detail="Item or cluster id doesn't exist")
            raise e

    @router.get(Routes.BASE_CLUSTER_ENDPOINT, response_model=GetCollectionsResponse)
    async def get_collections(
        cluster_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        filter={'ids': [cluster_id]} if cluster_id else None
        collections = await cluster_manager.get_collections(limit=limit, offset=offset, filter=filter, order_by='size')
        return GetCollectionsResponse(collections=collections)

    @router.patch(Routes.BASE_CLUSTER_ENDPOINT,  status_code=204)
    async def rename_cluster(cluster_id: str, label: str):
        await cluster_manager.rename(cluster_id, label)

    @router.get(Routes.COUNT_CLUSTERS_ENDPOINT, response_model=GetCountResponse)
    async def count_clusters():
        count = await cluster_manager.cluster_store.count()
        return GetCountResponse(count=count)

    @router.get(Routes.GET_CLUSTER_PLOT_ENDPOINT, response_class=Response)
    async def get_clusters_plot():
        img_bytes = await get_cluster_plot(cluster_manager)
        return Response(
            status_code=200 if img_bytes else 204,
            content=img_bytes,
            media_type="image/png",
        )

    @router.post(Routes.MERGE_CLUSTERS_ENDPOINT, response_model=MergeResponse)
    async def merge_clusters(req: MergeRequest):
        await cluster_manager.merge(req.primary_collection_id, req.secondary_collection_ids)
        collections = await cluster_manager.get_collections(filter={'ids': [req.primary_collection_id]}, limit=1)
        return MergeResponse(updated_collections=collections[0])

    return router