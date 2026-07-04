
from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import os
import asyncio
import time
import numpy as np

from dataclasses import asdict
from typing import get_args

from smartscan import ClusterResult, Cluster, ClusterMetadata
from smartscan.cluster import calculate_cluster_accuracy, IncrementalClusterer

from benchmarks.constants import  BENCHMARK_DIR
from benchmarks.utils import with_time, get_true_labels

from llm_connect.providers.openai import OpenAIProvider
from llm_connect.schemas.llm import LLMProviderConfig

from sereleum.constants.models import OPENAI_API_KEY, DEFAULT_SYSTEM_PROMPT, DEFAULT_OPENAI_MODEL
from sereleum.providers.types import TextEmbeddingModel
from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.clusters.plot import plot_clusters, plot_clusters_with_prototypes
from sereleum.utils.file import get_new_filename
from sereleum.logs import getLogger
from sereleum.data.db_config import get_config
from sereleum.clusters.helpers import get_prompt_cluster_manager

BENCHMARK_NAME = "clustering_benchmarks"
LOG_FILE_PATH = f"logs/{BENCHMARK_NAME}.log"

BENCHMARK_ASSIGNMENTS_PATH = os.path.join(BENCHMARK_DIR, f"assignments_{BENCHMARK_NAME}.jsonl")
BENCHMARK_PLOTS_DIR = os.path.join(BENCHMARK_DIR, "plots")
BENCHMARK_CLUSTERS_PLOT =  "prompt_clusters"

os.makedirs("logs", exist_ok=True)
os.makedirs(BENCHMARK_DIR, exist_ok=True)

logger = getLogger(BENCHMARK_NAME, LOG_FILE_PATH)

@with_time
def cluster(clusterer: IncrementalClusterer, ids, embeddings) -> tuple[ClusterResult, float]:
    return clusterer.cluster(ids, embeddings)

async def get_all_clusters(cluster_manager: ClusterManager):
    all_meta = await cluster_manager.cluster_store.get()
    all_cluster_embeds = await cluster_manager.cluster_embedding_store.get()
    return  { emb.item_id: Cluster(
        prototype_id=emb.item_id,
        embedding=emb.embedding,
        label = meta.label,
        metadata=ClusterMetadata(
            prototype_size=meta.prototype_size,
            mean_similarity=meta.mean_similarity,
            std_similarity=meta.std_similarity,
            label=meta.label
        )
    ) for emb, meta in zip(all_cluster_embeds, all_meta)}
    
# ids must be prefixed with label e.g promptlabel_123 for testing accuracy
async def run(cluster_manager: ClusterManager, model:TextEmbeddingModel, plot_output: str, default_threshold: float = 0.3, top_k: int = 5):
    results = {}    
    uncluster_embeds = await cluster_manager._get_unclustered_items()
    if not uncluster_embeds:
        logger.debug("No prompts to cluster")
        return
    cluster_result = await cluster_manager.cluster(auto_label=False)
    logger.debug(f"Assignments: {len(cluster_result.assignments)} | Clusters: {len(cluster_result.clusters)} | Merges: {len(cluster_result.merges)}")

    # if len(unlabelled) > 0:
    #    await clusters_manager.label_and_update(unlabelled)
    ids = list(cluster_result.assignments.keys())
    stored_embeds = await cluster_manager.item_embedding_store.get(ids)
    embeds = [e.embedding for e in stored_embeds]
    plot_clusters(ids, embeds, cluster_result.assignments, output_path=plot_output)
    cluster_ids = list(cluster_result.clusters.keys())
    prototype_embeddings = np.stack([cluster_result.clusters[cid].embedding for cid in cluster_ids], axis=0)
    filename = f"{os.path.basename(plot_output)}_with_proto"
    output = get_new_filename(BENCHMARK_PLOTS_DIR, filename, ".png")
    plot_clusters_with_prototypes(ids, embeds, cluster_result.assignments, cluster_ids, prototype_embeddings, output_path=output)

    true_labels = get_true_labels(ids)
    acc_info = calculate_cluster_accuracy(true_labels, cluster_result.assignments)
    bench = {"accuracy": asdict(acc_info), "clustering_speed": time}
    results[model] = bench
    logger.info(results)

    with open(BENCHMARK_ASSIGNMENTS_PATH, "w") as f:
        json.dump(cluster_result.assignments, f, indent=1, sort_keys=True)


async def run_real_benchmark(embedding_model: TextEmbeddingModel, embed_dim: int, default_threshold: float, top_k: int):
    llm = OpenAIProvider(OPENAI_API_KEY, LLMProviderConfig(model=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
    db_config = get_config()
    cluster_manager = get_prompt_cluster_manager(db_config, embed_dim=embed_dim, llm=llm)
    plot_output = get_new_filename(BENCHMARK_PLOTS_DIR, f"real_{BENCHMARK_CLUSTERS_PLOT}", ".png")
    await run(cluster_manager, embedding_model, plot_output, default_threshold=default_threshold, top_k=top_k)

def run_simulated_benchmark(n_items=10000, dim=384):
    """Benchmark the standard IncrementalClusterer."""
    ids = [str(i) for i in range(n_items)]
    embeddings = [np.random.rand(dim).astype(np.float32) for _ in range(n_items)]
    clusterer = IncrementalClusterer(default_threshold=0.3, top_k=5, benchmarking=True)
    start = time.time()
    clusterer.cluster(ids, embeddings)
    end = time.time()
    logger.info(f"IncrementalClusterer processed {n_items} items in {end - start:.4f}s")

def main():
    parser = argparse.ArgumentParser(description="Run clustering benchmarks")
    benchmark_type = parser.add_mutually_exclusive_group(required=True)
    benchmark_type.add_argument("--sim", "-s", action="store_true", help="Run simulated benchmark")
    benchmark_type.add_argument("--real", "-r", action="store_true", help="Run benchmark with real prompts data")

    parser.add_argument("--model","-m", help="Embedding model to use for indexing", default='all-minilm-l6-v2', choices=get_args(TextEmbeddingModel))
    parser.add_argument("--items", "-i", type=int, default=10000, help="Number of items for benchmark")
    parser.add_argument("--dim", "-d", type=int, default=384, help="Embedding dimension")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Top k nearest neighbours")
    parser.add_argument("--threshold", "-t", type=float, default=0.3, help="Default similarity threshold")

    args = parser.parse_args()

    if args.sim:
        run_simulated_benchmark(n_items=args.items, dim=args.dim)
    if args.real:
        asyncio.run(run_real_benchmark(args.model, args.dim, args.threshold, args.top_k))

if __name__ == "__main__":
    main()

