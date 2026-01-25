import json
import asyncio
import os
import argparse

from dotenv import load_dotenv

load_dotenv()
from dataclasses import asdict
from sereleum.types import Prompt
from sereleum.prompts.index.indexer import PromptIndexer
from sereleum.prompts.index.indexer_listener import  ProgressBarIndexerListener
from sereleum.data import get_dummy_data, get_placeholder_prompts
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.models.manage import ModelManager
from sereleum.embeddings.helpers import get_embedding_store
from benchmarks.constants import BENCHMARK_CHROMADB_PATH, BENCHMARK_DIR
from sereleum.models.manage import ModelManager
from sereleum.embeddings.helpers import get_embedding_store_persistent_file
from sereleum.prompts.index.indexer import PromptIndexer
from dotenv import load_dotenv

load_dotenv()

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

BENCHMARK_OUTPUT_PATH = os.path.join(BENCHMARK_DIR, "indexing_benchmarks.jsonl")

os.makedirs(BENCHMARK_DIR, exist_ok=True)

# `prompt_id` must be prefixed with label e.g promptlabel_123
# this is only for benchmarking
async def main(labelled_prompts: list[Prompt]):
    text_embedder = ModelManager().get_text_embedder('all-minilm-l6-v2')
    text_embedder.init()
    prompt_embedding_store =  get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'prompt', 'all-minilm-l6-v2', text_embedder.embedding_dim) 
    indexer =  PromptIndexer(text_embedder, listener=ProgressBarIndexerListener(), embeddings_store=prompt_embedding_store, batch_size=100, max_concurrency=4)
    result =  await indexer.run(labelled_prompts)
    result_dict = {k: v for k, v in asdict(result).items() if k != "error"}
    print(f"result - time_elpased: {result.time_elapsed} | processed: {result.total_processed}")
    with open(BENCHMARK_OUTPUT_PATH, "a") as f:
        f.write(json.dumps(result_dict, indent=None) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, help="number of items to generate", default=100)
    parser.add_argument("--stress", action="store_true", help="stress test")

    args = parser.parse_args()
    if args.n and args.stress:
        asyncio.run(main(get_dummy_data(args.n)))
    else:
        asyncio.run(main(get_placeholder_prompts()))
