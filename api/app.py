import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.schemas.response import GetPromptsOverviewResponse
from api.routers import Routes, create_items_router, create_clusters_router, create_events_router

from smartscan.models.model_manager import ModelManager

from llm_connect.schemas.llm import LLMProviderConfig
from llm_connect.providers.openai import OpenAIProvider

from sereleum.constants.db import POSTGRES_DSN
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.constants import  UPLOAD_DIR
from sereleum.data.helpers import create_sessionmaker

from domains.prompts import create_cluster_manager, Prompt
from domains.prompts.helpers import get_prompts_overview

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

model_manager = ModelManager()
text_embedder = model_manager.get_text_embedder("all-distilroberta-v1")
text_embedder.init()
llm = OpenAIProvider(OPENAI_API_KEY, LLMProviderConfig(model=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))

sessionmaker = create_sessionmaker(POSTGRES_DSN)
cluster_manager = create_cluster_manager(sessionmaker, llm)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_methods=["POST", "OPTIONS", "GET", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)

os.makedirs(UPLOAD_DIR, exist_ok=True)

app.include_router(create_items_router(Prompt, cluster_manager,text_embedder))
app.include_router(create_clusters_router(cluster_manager))
app.include_router(create_events_router())

@app.get(Routes.GET_PROMPTS_OVERVIEW_ENDPOINT, response_model=GetPromptsOverviewResponse)
async def get_overview():
    overview = await get_prompts_overview(cluster_manager)
    return GetPromptsOverviewResponse(**overview.model_dump())