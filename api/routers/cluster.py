from typing import Optional

from fastapi import APIRouter, HTTPException, Response

from api.schemas.request import MergeClustersRequest
from api.schemas.response import (
    GetCountResponse,
    GetClustersResponse,
    MergeResponse,
)
from sereleum.errors import SereleumError, ErrorCode
from sereleum.clusters.plot import get_cluster_plot
from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.data.types import TItem
from api.routers.routes import Routes


def create_clusters_router(cluster_manager: ClusterManager[TItem],) -> APIRouter:
    router = APIRouter()

    @router.patch(Routes.BASE_ITEMS_ENDPOINT,  status_code=204)
    async def move_item(item_id: str, cluster_id: str):
        try:
            await cluster_manager.move({item_id}, cluster_id)
        except SereleumError as e:
            if e.code == ErrorCode.INVALID_ARGUMENT:
                raise HTTPException(status_code=400, detail="Item or cluster id doesn't exist")
            raise e

    @router.get(Routes.BASE_CLUSTER_ENDPOINT, response_model=GetClustersResponse)
    async def get_clusters(
        cluster_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        if not cluster_id:
            clusters = await cluster_manager.cluster_store.get(limit=limit, offset=offset)
        else:
            clusters = await cluster_manager.cluster_store.get(
                filter={'ids': [cluster_id]}
            )
        return GetClustersResponse(clusters=clusters)

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
    async def merge_clusters(req: MergeClustersRequest):
        updated_clusters = await cluster_manager.merge(req.primary_collection_id, req.secondary_collection_ids)
        return MergeResponse(updated_clusters=updated_clusters)

    return router