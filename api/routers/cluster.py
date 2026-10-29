from typing import Optional

from fastapi import APIRouter, HTTPException, Response

from api.schemas.request import MergeClustersRequest
from api.schemas.response import (
    GetCountResponse,
    GetClustersResponse,
    RenameClusterResponse,
    MoveItemResponse,
    MergeResponse,
)
from sereleum.errors import SereleumError, ErrorCode
from sereleum.schemas.cluster import ClusterFilter
from sereleum.clusters.plot import get_cluster_plot
from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.data.types import TItem
from api.routers.routes import Routes


def create_clusters_router(cluster_manager: ClusterManager[TItem],) -> APIRouter:
    router = APIRouter()

    @router.patch(Routes.BASE_ITEMS_ENDPOINT, response_model=MoveItemResponse)
    async def move_item(item_id: str, cluster_id: str):
        try:
            await cluster_manager.assign({item_id: cluster_id})
        except SereleumError as e:
            if e.code == ErrorCode.INVALID_ARGUMENT:
                raise HTTPException(status_code=400, detail="Prompt or cluster id doesn't exist")
            raise
        return MoveItemResponse(updated_cluster_id=cluster_id)

    @router.get(Routes.BASE_CLUSTER_ENDPOINT, response_model=GetClustersResponse)
    async def get_clusters(
        cluster_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        if not cluster_id:
            clusters_orm = await cluster_manager.cluster_store.get(limit=limit, offset=offset)
        else:
            clusters_orm = await cluster_manager.cluster_store.get(
                filter=ClusterFilter(ids=[cluster_id])
            )
        clusters = cluster_manager.from_cluster_orm_list(clusters_orm)
        return GetClustersResponse(clusters=clusters)

    @router.patch(Routes.BASE_CLUSTER_ENDPOINT, response_model=RenameClusterResponse)
    async def rename_cluster(cluster_id: str, label: str):
        updated = await cluster_manager.update_label(cluster_id, label)
        if not updated:
            raise HTTPException(status_code=404, detail="Label doesn't exist")
        return RenameClusterResponse(updated_label=label)

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
        if not req.merges:
            raise HTTPException(status_code=400, detail="Merges cannot be empty")
        updated_clusters = await cluster_manager.merge(req.merges)
        return MergeResponse(updated_clusters=updated_clusters)

    return router