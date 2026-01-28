from dotenv import load_dotenv
load_dotenv()

import json
import asyncio
import os
import argparse

from dataclasses import asdict

from benchmarks.constants import BENCHMARK_CHROMADB_PATH, BENCHMARK_DIR

from sereleum.logs import getLogger
from sereleum.types import Prompt
from sereleum.index.indexer import PromptIndexer
from sereleum.index.indexer_listener import  ProgressBarIndexerListener
from sereleum.data import get_dummy_data, get_placeholder_prompts, get_test_prompts
from sereleum.utils.model_manager import ModelManager
from sereleum.embeddings.helpers import get_embedding_store_persistent_file

BENCHMARK_NAME = "indexing_benchmarks"
BENCHMARK_OUTPUT_PATH = os.path.join(BENCHMARK_DIR, f"{BENCHMARK_NAME}.jsonl")
LOG_FILE_PATH = f"logs/{BENCHMARK_NAME}.log"

os.makedirs("logs", exist_ok=True)
os.makedirs(BENCHMARK_DIR, exist_ok=True)

logger = getLogger(BENCHMARK_NAME, LOG_FILE_PATH)

# `prompt_id` must be prefixed with label e.g promptlabel_123
# this is only for benchmarking
async def main(labelled_prompts: list[Prompt]):
    text_embedder = ModelManager().get_text_embedder('all-minilm-l6-v2')
    text_embedder.init()
    prompt_embedding_store =  get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'prompt', 'all-minilm-l6-v2', text_embedder.embedding_dim) 
    indexer =  PromptIndexer(text_embedder, listener=ProgressBarIndexerListener(), embeddings_store=prompt_embedding_store, batch_size=100, max_concurrency=4)
    result =  await indexer.run(labelled_prompts)
    result_dict = {k: v for k, v in asdict(result).items() if k != "error"}
    logger.info(f"time_elpased: {result.time_elapsed} | processed: {result.total_processed}")
    with open(BENCHMARK_OUTPUT_PATH, "a") as f:
        f.write(json.dumps(result_dict, indent=None) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, help="number of items to generate", default=100)
    parser.add_argument("-o", type=int, help="dummy data offset", default=0)
    parser.add_argument("--stress", action="store_true", help="stress test")
    parser.add_argument("--test", action="store_true", help="use test prompts")

    args = parser.parse_args()
    if args.n and args.stress:
        asyncio.run(main(get_dummy_data(args.n, args.o)))
    elif args.test:
        asyncio.run(main(get_test_prompts()))
    else:
        asyncio.run(main(get_placeholder_prompts()))
