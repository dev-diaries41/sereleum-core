#!/usr/bin/env python3

import argparse
import uvicorn

from smartscan.models.model_manager import ModelManager

from llm_connect.providers.openai import OpenAIProvider
from llm_connect.schemas.llm import LLMProviderConfig

from sereleum.data.helpers import create_sessionmaker
from sereleum.constants.db import POSTGRES_DSN
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL

from domains.articles import create_cluster_manager, create_tag_manager, DomainItem
from domains.articles.workers import index_worker

from api.app import create_app


def main():
    model_manager = ModelManager()
    text_embedder = model_manager.get_text_embedder('all_distilroberta_v1')
    text_embedder.init()

    llm = OpenAIProvider(
        OPENAI_API_KEY,
        LLMProviderConfig(
            model=DEFAULT_OPENAI_MODEL,
            system_prompt=DEFAULT_SYSTEM_PROMPT,
        ),
    )

    sessionmaker = create_sessionmaker(POSTGRES_DSN)
    cluster_manager = create_cluster_manager(sessionmaker, llm)
    tag_manager = create_tag_manager(sessionmaker)

    return create_app(
        item_type=DomainItem,
        cluster_manager=cluster_manager,
        tag_manager=tag_manager,
        text_embedder=text_embedder,
        index_worker=index_worker
    )

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-p", type=int, default=8000)
    parser.add_argument("--workers", "-w", type=int, default=1)
    args = parser.parse_args()

    uvicorn.run(
        "main:main",
        factory=True,
        host="0.0.0.0",
        port=args.port,
        workers=args.workers,
    )


if __name__ == "__main__":
    cli()