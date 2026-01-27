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
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.clusters_manager import ClustersManager
from sereleum.providers.llm.openai import OpenAIClient
from sereleum.schemas.llm import LLMClientConfig
from sereleum.prompts.cluster import plot_clusters
from benchmarks.constants import BENCHMARK_CHROMADB_PATH, BENCHMARK_DIR
from sereleum.embeddings.helpers import get_embedding_store, get_embedding_store_persistent_file
from sereleum.providers.types import TextEmbeddingModel
from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL

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
async def run(prompts_manager: PromptsManager, clusters_manager: ClustersManager, model:TextEmbeddingModel, plot_output: str):
    results = {}
    ## NOTE: IncrementalClusterer uses random numbers internally. Running multiple models sequentially 
    # without reseeding causes non-deterministic clustering and lower accuracy. Reseed Python and 
    # before each clustering run to ensure reproducible results.

    random.seed(32)

    ids, metadatas, embeddings = prompts_manager.get_prompt_metadata_samples(1e5, exclude_clustered=True)
    print(f"N ids: {len(ids)}")
    existing_clusters = clusters_manager.get_all_clusters()
    existing_assignments = {prompt_id : metadata.cluster_id for prompt_id, metadata in zip(ids, metadatas)}
    clusterer = IncrementalClusterer(default_threshold=0.2, merge_threshold=0.9, top_k=5, existing_assignments=existing_assignments, existing_clusters=existing_clusters, benchmarking=True)  
    result,time = cluster(clusterer, ids, embeddings)
    print(f"Number assignments: {len(result.assignments)} | Number clusters: {len(result.clusters)}")
  
    if result.assignments:
        prompts_manager.update_prompts_from_assignments(result.assignments, result.merges)
    if result.clusters:
        unlabelled =  await clusters_manager.update_clusters(result.clusters, result.merges)
        print(f"Number unlabelled clusters: {len(unlabelled)}")

    # if len(unlabelled) > 0:
    #    await clusters_manager.label_and_update_clusters(unlabelled)

    if ids and embeddings:
        plot_clusters(ids, embeddings, result.assignments, output_path=plot_output)
    acc_info = clusters_manager.calculate_cluster_accuracy()
    bench = {"accuracy": asdict(acc_info), "clustering_speed": time}
    results[model] = bench
 
    print(results)

    with open(BENCHMARK_OUTPUT_PATH, "a") as f:
        f.write(json.dumps(results, indent=None) + "\n")

    # Save last result assignments
    with open(BENCHMARK_ASSIGNMENTS_PATH, "w") as f:
        json.dump(result.assignments, f, indent=1, sort_keys=True)



def get_prompt_manager():
    prompt_embedding_store = get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'prompt', 'all-minilm-l6-v2', 384) 
    return  PromptsManager(embedding_store=prompt_embedding_store)


def get_cluster_manager(prompt_manager: PromptsManager, llm):
    cluster_embedding_store = get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'cluster', 'all-minilm-l6-v2', 384) 
    return  ClustersManager(embedding_store=cluster_embedding_store, prompts_manager=prompt_manager, llm=llm)

async def main():
    llm = OpenAIClient(OPENAI_API_KEY, LLMClientConfig(model_name=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
    prompts_manager =get_prompt_manager()
    clusters_manager = get_cluster_manager(prompts_manager, llm)
    plot_output = get_new_filename(BENCHMARK_PLOTS_DIR, BENCHMARK_CLUSTERS_PLOT, ".png")
    await run(prompts_manager, clusters_manager, 'all-minilm-l6-v2', plot_output)

asyncio.run(main())