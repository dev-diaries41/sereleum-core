import os

from dramatiq import Actor

from typing import Type

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import create_items_router, create_clusters_router, create_events_router, create_tags_router

from smartscan import TextEmbeddingProvider

from sereleum.constants import  UPLOAD_DIR
from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.tags.tag_manager import TagManager

from sereleum.data.types import TItem


def create_app(
    item_type: Type[TItem], 
    cluster_manager: ClusterManager[TItem],
    tag_manager: TagManager,
    index_worker: Actor, 
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
        allow_headers=allow_headers if allow_headers is not None else ["*"],
        max_age=3600,
    )

    app.include_router(create_items_router(item_type, cluster_manager,text_embedder, index_worker))
    app.include_router(create_clusters_router(cluster_manager))
    app.include_router(create_tags_router(tag_manager))
    app.include_router(create_events_router())
    return app