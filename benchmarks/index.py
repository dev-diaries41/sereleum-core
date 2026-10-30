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
from sereleum.data.embeds.helpers import get_embed_store_name
from sereleum.providers.types import TextEmbeddingModel
from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore
from sereleum.index.progressbar_index_listener import ProgressBarIndexerListener
from sereleum.data.types import TItem

from domains.prompts.stores.item_store import PromptStore
from domains.prompts.item import Prompt
from domains.prompts.indexer import PromptIndexer
from domains.articles.stores.item_store import ArticleStore
from domains.articles.item import Article
from domains.articles.indexer import ArticleIndexer


BENCHMARK_NAME = "indexing_benchmarks"
LOG_FILE_PATH = f"logs/{BENCHMARK_NAME}.log"

os.makedirs("logs", exist_ok=True)
os.makedirs(BENCHMARK_DIR, exist_ok=True)

logger = getLogger(BENCHMARK_NAME, LOG_FILE_PATH)

async def index_prompts(items: list[Prompt], model: TextEmbeddingModel):
    text_embedder = ModelManager().get_text_embedder(model)
    text_embedder.init()
    sessionmaker = create_sessionmaker(POSTGRES_DSN)
    item_store = PromptStore(sessionmaker)
    prompt_embed_store = PgVectorEmbeddingStore(name =get_embed_store_name(model, 'item_test'), sessionmaker=sessionmaker)
    indexer =  PromptIndexer(text_embedder, listener=ProgressBarIndexerListener(), embeddings_store=prompt_embed_store, prompt_store=item_store, batch_size=100, max_concurrency=4)
    result =  await indexer.run(items)
    logger.info(f"time_elpased: {result.time_elapsed} | processed: {result.total_processed}")

async def index_articles(items: list[Article], model: TextEmbeddingModel):
    text_embedder = ModelManager().get_text_embedder(model)
    text_embedder.init()
    sessionmaker = create_sessionmaker(POSTGRES_DSN)
    item_store = ArticleStore(sessionmaker)
    item_embed_store = PgVectorEmbeddingStore(name = get_embed_store_name(model, 'article_test'), sessionmaker=sessionmaker)
    indexer =  ArticleIndexer(text_embedder, listener=ProgressBarIndexerListener(), embed_store=item_embed_store, item_store=item_store, batch_size=100, max_concurrency=4)
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
    if args.seed:
        random.seed(args.seed)

    if args.n and args.stress:
        asyncio.run(index_prompts(get_dummy_data(args.n, args.o), args.model))
    elif args.file:
        items = load_items(args.file, Article)
        asyncio.run(index_articles(items, args.model))
    elif args.dir:
        all_items = []
        for filename in os.listdir(args.dir):
            filepath = os.path.join(args.dir, filename)
            items = load_items(filepath, Article)
            all_items.extend(items)
        if args.seed:
            random.shuffle(all_items, args.model)
        asyncio.run(index_articles(all_items, args.model))