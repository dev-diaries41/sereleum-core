import asyncio
import os
import argparse
import random

from dotenv import load_dotenv
load_dotenv('.env.local')

from typing import get_args

from smartscan.models.model_manager import ModelManager
from benchmarks.constants import BENCHMARK_DIR

from sereleum.constants.db import POSTGRES_DSN
from sereleum.utils.data import get_dummy_data
from sereleum.logs import getLogger
from sereleum.data.helpers import create_sessionmaker
from sereleum.utils.file import load_items
from sereleum.providers.types import TextEmbeddingModel
from sereleum.index.progressbar_index_listener import ProgressBarIndexerListener
from sereleum.data.types import TItem

from domains.prompts import Prompt, create_indexer as create_prompts_indexer
from domains.articles import Article, create_indexer as create_articles_indexer



BENCHMARK_NAME = "indexing_benchmarks"
LOG_FILE_PATH = f"logs/{BENCHMARK_NAME}.log"

os.makedirs("logs", exist_ok=True)
os.makedirs(BENCHMARK_DIR, exist_ok=True)

logger = getLogger(BENCHMARK_NAME, LOG_FILE_PATH)
sessionmaker = create_sessionmaker(POSTGRES_DSN)

async def index_prompts(items: list[Prompt], text_embedder):
    indexer = create_prompts_indexer(text_embedder, sessionmaker, batch_size=100, max_concurrency=4)
    indexer.register_listener(ProgressBarIndexerListener())
    result =  await indexer.run(items)
    logger.info(f"time_elpased: {result.time_elapsed} | processed: {result.total_processed}")

async def index_articles(items: list[Article], text_embedder):
    indexer = create_articles_indexer(text_embedder, sessionmaker, batch_size=100, max_concurrency=4)
    indexer.register_listener(ProgressBarIndexerListener())
    result =  await indexer.run(items)
    logger.info(f"time_elpased: {result.time_elapsed} | processed: {result.total_processed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model","-m", help="Embedding model to use for indexing", default='all_distilroberta_v1', choices=get_args(TextEmbeddingModel))
    parser.add_argument("-n", type=int, help="number of items to generate", default=100)
    parser.add_argument("-o", type=int, help="dummy data offset", default=0)
    parser.add_argument("--stress", action="store_true", help="stress test")
    parser.add_argument("--file", "-f", help="JSON prompts filepath")
    parser.add_argument("--dir", "-d", help="Directory with json prompt files")
    parser.add_argument("--seed", type=int, default=None)

    args = parser.parse_args()

    text_embedder = ModelManager().get_text_embedder(args.model)
    text_embedder.init()

    if args.seed:
        random.seed(args.seed)

    if args.n and args.stress:
        asyncio.run(index_prompts(get_dummy_data(args.n, args.o), text_embedder))
    elif args.file:
        items = load_items(args.file, Article)
        asyncio.run(index_articles(items,text_embedder))
    elif args.dir:
        all_items = []
        for filename in os.listdir(args.dir):
            filepath = os.path.join(args.dir, filename)
            items = load_items(filepath, Article)
            all_items.extend(items)
        if args.seed:
            random.shuffle(all_items)
        asyncio.run(index_articles(all_items, text_embedder))