from typing import Optional

from fastapi import APIRouter, HTTPException

from api.schemas.request import MergeRequest, TagRequest, MoveRequest, DeleteTagsRequest
from api.schemas.response import GetCountResponse,  MergeResponse, GetCollectionsResponse
from sereleum.errors import SereleumError, ErrorCode
from sereleum.tags.tag_manager import TagManager
from api.routers.routes import Routes


def create_tags_router(tag_manager: TagManager) -> APIRouter:
    router = APIRouter()

    @router.get(Routes.BASE_TAG_ENDPOINT, response_model=GetCollectionsResponse)
    async def get_collections(
        tag_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        filter={'ids': [tag_id]} if tag_id else None
        collections = await tag_manager.get_collections(limit=limit, offset=offset, filter=filter)
        return GetCollectionsResponse(collections=collections)

    # @router.patch(Routes.MOVE_TAG_ITEMS_ENDPOINT, status_code=204)
    # async def move_items(req: MoveRequest):
    #     if not isinstance(req.new_collection_id, int) or not isinstance(req.current_collection_id, int):
    #         raise HTTPException(status_code=400, detail="Collection id must be of type int")
    #     if not req.current_collection_id:
    #         raise HTTPException(status_code=400, detail="Missing current_collection_id")
        
    #     try:
    #         await tag_manager.move(set(req.item_ids), req.new_collection_id, req.current_collection_id)
    #     except SereleumError as e:
    #         if e.code == ErrorCode.INVALID_ARGUMENT:
    #             raise HTTPException(status_code=400, detail="Item or cluster id doesn't exist")
    #         raise

    @router.patch(Routes.BASE_TAG_ENDPOINT,  status_code=204)
    async def rename_tag(collection_id: int, name: str):
        await tag_manager.rename(collection_id, name)

    @router.get(Routes.COUNT_TAGS_ENDPOINT, response_model=GetCountResponse)
    async def count_tags():
        count = await tag_manager.tag_store.count()
        return GetCountResponse(count=count)


    @router.post(Routes.MERGE_TAGS_ENDPOINT, response_model=MergeResponse)
    async def merge_tags(req: MergeRequest):
        await tag_manager.merge(req.primary_collection_id, req.secondary_collection_ids)
        collections = await tag_manager.get_collections(filter={'ids': [req.primary_collection_id]}, limit=1)
        return MergeResponse(merged_collection=collections[0])

    
    @router.post(Routes.TAG_ITEMS_ENDPOINT, status_code=204)
    async def tag(req: TagRequest):
        await tag_manager.tag(req.tag, req.collection_id, req.item_ids, select_all=req.select_all, excluded_item_ids=req.excluded_item_ids)


    @router.post(Routes.DELETE_TAGS_ENDPOINT, status_code=204)
    async def delete_tags(req: DeleteTagsRequest):
        await tag_manager.delete(req.collection_ids)
            
    return router