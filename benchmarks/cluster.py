
from dotenv import load_dotenv
load_dotenv()

import argparse
import random
import json
import os
import asyncio
import numpy as np
import time

from dataclasses import asdict

from smartscan import ClusterResult
from smartscan.cluster import IncrementalClusterer, calculate_cluster_accuracy

from benchmarks.constants import BENCHMARK_CHROMADB_PATH, BENCHMARK_DIR
from benchmarks.utils import with_time

from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.providers.types import TextEmbeddingModel
from sereleum.store.items_manager import ItemsManager
from sereleum.store.clusters_manager import ClustersManager
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.clusters_manager import PromptClustersManager
from sereleum.providers.llm.openai import OpenAIClient
from sereleum.schemas.llm import LLMClientConfig
from sereleum.store.helpers import get_embedding_store_persistent_file
from sereleum.cluster import plot_clusters, plot_clusters_with_prototypes, get_assignments_and_labels
from sereleum.utils.file import get_new_filename
from sereleum.logs import getLogger

BENCHMARK_NAME = "clustering_benchmarks"
LOG_FILE_PATH = f"logs/{BENCHMARK_NAME}.log"
BENCHMARK_OUTPUT_PATH = os.path.join(BENCHMARK_DIR, f"{BENCHMARK_NAME}.jsonl")
BENCHMARK_ASSIGNMENTS_PATH = os.path.join(BENCHMARK_DIR, f"assignments_{BENCHMARK_NAME}.jsonl")
BENCHMARK_PLOTS_DIR = os.path.join(BENCHMARK_DIR, "plots")
BENCHMARK_CLUSTERS_PLOT =  "prompt_clusters"

os.makedirs("logs", exist_ok=True)
os.makedirs(BENCHMARK_DIR, exist_ok=True)

logger = getLogger(BENCHMARK_NAME, LOG_FILE_PATH)

@with_time
def cluster(clusterer: IncrementalClusterer, ids, embeddings) -> tuple[ClusterResult, float]:
    return clusterer.cluster(ids, embeddings)

# `prompt_id` must be prefixed with label e.g promptlabel_123
# this is only for benchmarking
async def run(items_manager: ItemsManager, clusters_manager: ClustersManager, model:TextEmbeddingModel, plot_output: str, default_threshold: float = 0.3, merge_threshold: float = 0.9, top_k: int = 5):
    results = {}
    ## NOTE: IncrementalClusterer uses random numbers internally. Running multiple models sequentially 
    # without reseeding causes non-deterministic clustering and lower accuracy. Reseed Python and 
    # before each clustering run to ensure reproducible results.
    random.seed(32)
    
    ids, metadatas, embeddings = items_manager.get_samples(1e5, exclude_clustered=False)
    if not ids:
        logger.debug("No prompts to cluster")
        return
    existing_clusters = clusters_manager.get_all_clusters()
    existing_assignments = {prompt_id : metadata.cluster_id for prompt_id, metadata in zip(ids, metadatas)}
    clusterer = IncrementalClusterer(default_threshold=default_threshold, merge_threshold=merge_threshold, top_k=top_k, existing_assignments=existing_assignments, existing_clusters=existing_clusters, benchmarking=True)  
    result,time = cluster(clusterer, ids, embeddings)
    logger.debug(f"Number assignments: {len(result.assignments)} | Number clusters: {len(result.clusters)}")
    if result.assignments:
        items_manager.update_from_assignments(result.assignments, result.merges)
    if result.clusters:
        unlabelled =  await clusters_manager.update(result.clusters, result.merges)
        logger.debug(f"Number unlabelled clusters: {len(unlabelled)}")
    # if len(unlabelled) > 0:
    #    await clusters_manager.label_and_update(unlabelled)
    if ids and embeddings:
        plot_clusters(ids, embeddings, result.assignments, output_path=plot_output)

        cluster_ids = list(result.clusters.keys())
        prototype_embeddings = np.stack([result.clusters[cid].embedding for cid in cluster_ids], axis=0)
        filename = f"{os.path.basename(plot_output)}_with_proto"
        output = get_new_filename(BENCHMARK_PLOTS_DIR, filename, ".png")

        plot_clusters_with_prototypes(ids=ids, embeddings=embeddings, assignments=result.assignments, prototype_embeddings=prototype_embeddings, prototype_ids=cluster_ids, output_path=output)
    true_labels, assignments = get_assignments_and_labels(items_manager)
    acc_info = calculate_cluster_accuracy(true_labels, assignments)
    bench = {"accuracy": asdict(acc_info), "clustering_speed": time}
    results[model] = bench
    logger.info(results)

    with open(BENCHMARK_ASSIGNMENTS_PATH, "w") as f:
        json.dump(result.assignments, f, indent=1, sort_keys=True)



def get_prompt_manager():
    embedding_store = get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'prompt', 'all-minilm-l6-v2', 384) 
    return PromptsManager(embedding_store=embedding_store)

def get_cluster_manager(prompt_manager: PromptsManager, llm):
    embedding_store = get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'cluster', 'all-minilm-l6-v2', 384)
    return PromptClustersManager(embedding_store=embedding_store, items_manager=prompt_manager, llm=llm)

async def run_real_benchmark(default_threshold: float = 0.3, merge_threshold: float = 0.9, top_k: int = 5):
    llm = OpenAIClient(OPENAI_API_KEY, LLMClientConfig(model_name=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
    prompts_manager = get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager, llm)
    plot_output = get_new_filename(BENCHMARK_PLOTS_DIR, f"real_{BENCHMARK_CLUSTERS_PLOT}", ".png")
    await run(prompts_manager, clusters_manager, 'all-minilm-l6-v2', plot_output, default_threshold=default_threshold, merge_threshold=merge_threshold, top_k=top_k)


def run_simulated_benchmark(n_items=10000, dim=384):
    """Benchmark the standard IncrementalClusterer."""
    ids = [str(i) for i in range(n_items)]
    embeddings = [np.random.rand(dim).astype(np.float32) for _ in range(n_items)]
    clusterer = IncrementalClusterer(default_threshold=0.3, top_k=5, merge_threshold=0.9, benchmarking=True)
    start = time.time()
    clusterer.cluster(ids, embeddings)
    end = time.time()
    logger.info(f"IncrementalClusterer processed {n_items} items in {end - start:.4f}s")


def main():
    parser = argparse.ArgumentParser(description="Run clustering benchmarks")
    parser.add_argument("--sim", "-s", action="store_true", help="Run simulated benchmark")
    parser.add_argument("--real", "-r", action="store_true", help="Run benchmark with real prompts data")
    parser.add_argument("--items", "-i", type=int, default=10000, help="Number of items for benchmark")
    parser.add_argument("--dim", "-d", type=int, default=384, help="Embedding dimension for benchmark")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Top k nearest neighbours")
    parser.add_argument("--merge-threshold", "-m", type=float, default=0.9, help="Required similarity threshold for merging clusters")
    parser.add_argument("--threshold", "-t", type=float, default=0.3, help="Default similarity threshold")

    args = parser.parse_args()

    if args.sim:
        run_simulated_benchmark(n_items=args.items, dim=args.dim)
    if args.real:
        asyncio.run(run_real_benchmark(args.threshold, args.merge_threshold, args.top_k))
    if not args.sim and not args.real:
        print("No benchmark selected. Use --standard, --vectorized, or --real.")


if __name__ == "__main__":
    main()

