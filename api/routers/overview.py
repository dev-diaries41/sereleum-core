from fastapi import  APIRouter

from api.routers.routes import Routes
from api.schemas.response import GetOverviewResponse

from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.tags.tag_manager import TagManager
from sereleum.data.types import TItem

def create_overview_router(
        tag_manager: TagManager, 
        cluster_manager: ClusterManager[TItem], 
        ) -> APIRouter:
    
    router = APIRouter()

    @router.get(Routes.GET_OVERVIEW_ENDPOINT, response_model=GetOverviewResponse)
    async def get_overview():
        await _get_overview(tag_manager, cluster_manager)

    return router

async def _get_overview( tag_manager: TagManager, cluster_manager: ClusterManager[TItem] ):
    top_cluster_collections = await cluster_manager.get_collections(order_by='size', limit=6, ascending=False)
    top_tag_collections = await tag_manager.get_collections(order_by='size', limit=6, ascending=False)
    clusters_count = await cluster_manager.cluster_store.count()
    tags_count = await tag_manager.tag_store.count()
    items_count = await cluster_manager.item_store.count()
    return GetOverviewResponse(
        total_items=items_count,
        total_clusters=clusters_count,
        total_tags=tags_count,
        top_clusters=top_cluster_collections,
        top_tags=top_tag_collections
    )