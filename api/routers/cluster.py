from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from smartscan import TextEmbeddingProvider

from api.routers.routes import Routes
from api.schemas.request import MergeRequest, MoveRequest, DeleteClusterRequest, CreateClusterRequest
from api.schemas.response import GetCountResponse, GetCollectionsResponse, MergeResponse, CreateClusterResponse

from sereleum.errors import SereleumError, ErrorCode
from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.data.types import TItem


def create_clusters_router(
        cluster_manager: ClusterManager[TItem],
        text_embedder: TextEmbeddingProvider,
        ) -> APIRouter:
    router = APIRouter()

    @router.patch(Routes.MOVE_CLUSTER_ITEMS_ENDPOINT,  status_code=204)
    async def move_items(req: MoveRequest):
        if not isinstance(req.destination_collection_id, str) or not isinstance(req.source_collection_id, str):
            raise HTTPException(status_code=400, detail="Collection id must be of type str")
        
        try:
            await cluster_manager.move(req.destination_collection_id, req.source_collection_id, req.item_ids, select_all=req.select_all, excluded_item_ids=req.excluded_item_ids)
        except SereleumError as e:
            if e.code == ErrorCode.INVALID_ARGUMENT:
                raise HTTPException(status_code=400, detail="Item or cluster id doesn't exist")
            raise e

    @router.get(Routes.BASE_CLUSTER_ENDPOINT, response_model=GetCollectionsResponse)
    async def get_collections(
        collection_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        filter={'ids': [collection_id]} if collection_id else None
        collections = await cluster_manager.get_collections(limit=limit, offset=offset, filter=filter, order_by='size')
        return GetCollectionsResponse(collections=collections)

    @router.patch(Routes.BASE_CLUSTER_ENDPOINT,  status_code=204)
    async def rename_cluster(collection_id: str, name: str):
        await cluster_manager.rename(collection_id, name)

    @router.get(Routes.COUNT_CLUSTERS_ENDPOINT, response_model=GetCountResponse)
    async def count_clusters():
        count = await cluster_manager.cluster_store.count()
        return GetCountResponse(count=count)
    

    @router.post(Routes.MERGE_CLUSTERS_ENDPOINT, response_model=MergeResponse)
    async def merge_clusters(req: MergeRequest):
        await cluster_manager.merge(req.primary_collection_id, req.secondary_collection_ids)
        collections = await cluster_manager.get_collections(filter={'ids': [req.primary_collection_id]}, limit=1)
        return MergeResponse(merged_collection=collections[0])

    @router.post(Routes.DELETE_CLUSTERS_ENDPOINT, status_code=204)
    async def delete_clusters(req: DeleteClusterRequest):
        await cluster_manager.delete(req.collection_ids)

    @router.post(Routes.CREATE_CLUSTER_ENDPOINT, response_model=CreateClusterResponse)
    async def create_cluster(req: CreateClusterRequest):
        embed = (await run_in_threadpool(text_embedder.embed, req.seed))[0]
        cluster_id = await cluster_manager.create(req.name, embed)
        return CreateClusterResponse(cluster_id=cluster_id)
            
    return router