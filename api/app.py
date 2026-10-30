import os

from typing import Type
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import create_items_router, create_clusters_router, create_events_router

from smartscan import TextEmbeddingProvider

from sereleum.constants import  UPLOAD_DIR
from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.data.types import TItem


def create_app(
    item_type: Type[TItem], 
    cluster_manager: ClusterManager[TItem], 
    text_embedder: TextEmbeddingProvider,
    allow_origins: list[str] | None = None,
    allow_headers: list[str] | None = None,
    ):
 
    app = FastAPI()

    os.makedirs(UPLOAD_DIR, exist_ok=True)


    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_methods=["POST", "OPTIONS", "GET", "PATCH"],
        allow_headers=["*"],
        allow_headers=allow_headers if allow_headers is not None else ["*"],
        max_age=3600,
    )

    app.include_router(create_items_router(item_type, cluster_manager,text_embedder))
    app.include_router(create_clusters_router(cluster_manager))
    app.include_router(create_events_router())
    return app

# @app.get(Routes.GET_PROMPTS_OVERVIEW_ENDPOINT, response_model=GetPromptsOverviewResponse)
# async def get_overview():
#     overview = await get_prompts_overview(cluster_manager)
#     return GetPromptsOverviewResponse(**overview.model_dump())