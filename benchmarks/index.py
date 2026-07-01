from dotenv import load_dotenv
load_dotenv()

import json
import asyncio
import os
import argparse
import random
import chromadb

from typing import get_args
from benchmarks.constants import BENCHMARK_CHROMADB_PATH, BENCHMARK_DIR

from smartscan.models.model_manager import ModelManager
from smartscan.index.listener import ProgressBarIndexerListener

from sereleum.types import Prompt
from sereleum.index.prompts.indexer import PromptIndexer
from sereleum.store.chroma_store import ChromaDBEmbeddingStore
from sereleum.providers.types import TextEmbeddingModel
from sereleum.data import get_dummy_data
from sereleum.logs import getLogger
from sereleum.helpers import get_embedding_collection_name

BENCHMARK_NAME = "indexing_benchmarks"
LOG_FILE_PATH = f"logs/{BENCHMARK_NAME}.log"

os.makedirs("logs", exist_ok=True)
os.makedirs(BENCHMARK_DIR, exist_ok=True)

logger = getLogger(BENCHMARK_NAME, LOG_FILE_PATH)
client = chromadb.PersistentClient(path=BENCHMARK_CHROMADB_PATH, settings=chromadb.Settings(anonymized_telemetry=False))

# `prompt_id` must be prefixed with label e.g promptlabel_123
# this is only for benchmarking
async def main(labelled_prompts: list[Prompt], model: TextEmbeddingModel):
    text_embedder = ModelManager().get_text_embedder(model)
    text_embedder.init()
    collection_name = get_embedding_collection_name("prompt", model, text_embedder.embedding_dim)
    embedding_store = ChromaDBEmbeddingStore(client.get_or_create_collection(collection_name))
    indexer =  PromptIndexer(text_embedder, listener=ProgressBarIndexerListener(), embeddings_store=embedding_store, batch_size=100, max_concurrency=4)
    result =  await indexer.run(labelled_prompts)
    logger.info(f"time_elpased: {result.time_elapsed} | processed: {result.total_processed}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model","-m", help="Embedding model to use for indexing", default='all-minilm-l6-v2', choices=get_args(TextEmbeddingModel))
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
        asyncio.run(main(get_dummy_data(args.n, args.o), args.model))
    elif args.file:
        with open(args.file) as f:
            prompts = [Prompt(**p) for p in json.load(f)]
        asyncio.run(main(prompts, args.model))
    elif args.dir:
        all_prompts = []
        for filename in os.listdir(args.dir):
            filepath = os.path.join(args.dir, filename)
            with open(filepath) as f:
                all_prompts.extend([Prompt(**p) for p in json.load(f)])
        
        if args.seed:
            random.shuffle(all_prompts, args.model)

        asyncio.run(main(all_prompts, args.model))

