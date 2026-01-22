import random
import json
import os
import asyncio

from dotenv import load_dotenv
load_dotenv()

from dataclasses import asdict
from smartscan import ClusterResult
from smartscan.classify import IncrementalClusterer
from sereleum.utils import with_time, get_new_filename
from sereleum.prompts_manager import PromptsManager
from sereleum.cluster import plot_clusters
from benchmarks.constants import BENCHMARK_CHROMADB_PATH, BENCHMARK_DIR
from sereleum.embeddings.helpers import get_embedding_store
from sereleum.providers.types import TextEmbeddingModel

BENCHMARK_OUTPUT_PATH = os.path.join(BENCHMARK_DIR, "clustering_benchmarks.jsonl")
BENCHMARK_ASSIGNMENTS_PATH = os.path.join(BENCHMARK_DIR, "assignments_clustering_benchmarks.jsonl")
BENCHMARK_PLOTS_DIR = os.path.join(BENCHMARK_DIR, "plots")
BENCHMARK_CLUSTERS_PLOT =  "prompt_clusters"

os.makedirs(BENCHMARK_DIR, exist_ok=True)

@with_time
def cluster(clusterer: IncrementalClusterer, ids, embeddings) -> tuple[ClusterResult, float]:
    return clusterer.cluster(ids, embeddings)

# `prompt_id` must be prefixed with label e.g promptlabel_123
# this is only for benchmarking
async def run(prompts_manager: PromptsManager, model:TextEmbeddingModel, plot_output: str):
    results = {}
    ## NOTE: IncrementalClusterer uses random numbers internally. Running multiple models sequentially 
    # without reseeding causes non-deterministic clustering and lower accuracy. Reseed Python and 
    # before each clustering run to ensure reproducible results.

    random.seed(32)

    ids, embeddings, cluster_ids = prompts_manager.get_all_prompt_embeddings()
    existing_clusters = prompts_manager.get_all_clusters()
    existing_assignments = dict(zip(ids, cluster_ids))
    clusterer = IncrementalClusterer(default_threshold=0.55, sim_factor=0.9, merge_threshold=0.9, existing_assignments=existing_assignments, existing_clusters=existing_clusters, benchmarking=True)  
    result,time = cluster(clusterer, ids, embeddings)
    if ids and embeddings:
        # Plot to visualise prompt clusters
        plot_clusters(ids, embeddings, result.assignments, output_path=plot_output)
    acc_info = prompts_manager.calculate_cluster_accuracy()
    bench = {"accuracy": asdict(acc_info), "clustering_speed": time}
    results[model] = bench
 
    if result.assignments:
        prompts_manager.update_prompts(result.assignments, result.merges)
    if result.clusters:
        await prompts_manager.update_clusters(result.clusters, result.merges)

    print(results)

    with open(BENCHMARK_OUTPUT_PATH, "a") as f:
        f.write(json.dumps(results, indent=None) + "\n")

    # Save last result assignments
    with open(BENCHMARK_ASSIGNMENTS_PATH, "w") as f:
        json.dump(result.assignments, f, indent=1, sort_keys=True)


async def main():
    prompt_embedding_store =  get_embedding_store(BENCHMARK_CHROMADB_PATH, PromptsManager.PROMPT_TYPE, 'all-minilm-l6-v2', 384) 
    cluster_embedding_store =  get_embedding_store(BENCHMARK_CHROMADB_PATH, PromptsManager.CLUSTER_TYPE, 'all-minilm-l6-v2', 384) 
    prompts_manager = PromptsManager(prompt_embedding_store=prompt_embedding_store, cluster_embedding_store=cluster_embedding_store)
    plot_output = get_new_filename(BENCHMARK_PLOTS_DIR, BENCHMARK_CLUSTERS_PLOT, ".png")
    run(prompts_manager, 'all-minilm-l6-v2', plot_output)

asyncio.run(main())