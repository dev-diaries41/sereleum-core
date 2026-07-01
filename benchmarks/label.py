
from dotenv import load_dotenv
load_dotenv()

import json
import os
import chromadb
import argparse

from typing import get_args

from benchmarks.constants import BENCHMARK_CHROMADB_PATH, BENCHMARK_DIR

from llm_connect.providers.openai import OpenAIProvider
from llm_connect.schemas.llm import LLMProviderConfig

from sereleum.constants.models import DEFAULT_SYSTEM_PROMPT, OPENAI_API_KEY, DEFAULT_OPENAI_MODEL
from sereleum.helpers import get_prompt_manager, get_cluster_manager
from sereleum.providers.types import TextEmbeddingModel


BENCHMARK_OUTPUT_PATH = os.path.join(BENCHMARK_DIR, "labelling_benchmarks.jsonl")

os.makedirs(BENCHMARK_DIR, exist_ok=True)


def run(model: TextEmbeddingModel, embed_dim: int):
    llm = OpenAIProvider(OPENAI_API_KEY, LLMProviderConfig(model=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
    client = chromadb.PersistentClient(path=BENCHMARK_CHROMADB_PATH, settings=chromadb.Settings(anonymized_telemetry=False))
    prompts_manager = get_prompt_manager(client, model, embed_dim)
    clusters_manager = get_cluster_manager(client, model, embed_dim, prompts_manager, llm)
    clusters = clusters_manager.get_clusters(limit=1)
    if not clusters:
        raise ValueError("No existing clusters")
    sample_size = 10
    cluser_id = list(clusters.keys())[0]
    result = clusters_manager.label(cluser_id, sample_size, [])
    print(result)
    
    with open(BENCHMARK_OUTPUT_PATH, "a") as f:
        json.dump(result.model_dump(), f, indent=1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run label benchamrk")
    parser.add_argument("--model","-m", help="Embedding model to use for indexing", default='all-minilm-l6-v2', choices=get_args(TextEmbeddingModel))
    parser.add_argument("--dim", "-d", type=int, default=384, help="Embedding dimension")

    run()