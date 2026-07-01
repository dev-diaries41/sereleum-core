
from dotenv import load_dotenv
load_dotenv()

import json
import os

from benchmarks.constants import BENCHMARK_CHROMADB_PATH, BENCHMARK_DIR

from llm_connect.providers.openai import OpenAIProvider
from llm_connect.schemas.llm import LLMProviderConfig
from llm_connect.providers.llm_provider import LLMProvider

from sereleum.constants.models import DEFAULT_SYSTEM_PROMPT, OPENAI_API_KEY, DEFAULT_OPENAI_MODEL
from sereleum.items.prompt_manager import PromptManager
from sereleum.clusters.prompt_cluster_manager import PromptClusterManager
from sereleum.store.helpers import get_embedding_store_persistent_file
from sereleum.schemas.llm import LLMClassificationResult


BENCHMARK_OUTPUT_PATH = os.path.join(BENCHMARK_DIR, "labelling_benchmarks.jsonl")

os.makedirs(BENCHMARK_DIR, exist_ok=True)



def label_cluster(llm: LLMProvider, cluster_manager: PromptClusterManager, prompts_manager: PromptManager, cluster_id: str, sample_size: int, existing_labels: list[str]) -> LLMClassificationResult:
    clusters = cluster_manager.get_clusters(cluster_ids=[cluster_id], include=['embeddings'])
    if not clusters:
        raise ValueError("Cluster not found")
    prompts = prompts_manager.embedding_store.query(query_embeds=[clusters[cluster_id].embedding], filter={"cluster_id": cluster_id},  limit=sample_size, include=['documents'])
    print(f"Found {len(prompts.ids)} similar prompts_____________\n")
    print(prompts.ids)
    return cluster_manager.label(cluster_id, sample_size, existing_labels)

def run(llm: OpenAIProvider, cm: PromptClusterManager, pm: PromptManager, cluster_id: str, sample_size: int):
    result = label_cluster(llm, cm, pm, cluster_id, sample_size, [])
    print(result)
    
    with open(BENCHMARK_OUTPUT_PATH, "a") as f:
        json.dump(result.model_dump(), f, indent=1)

def main():
    llm = OpenAIProvider(OPENAI_API_KEY, LLMProviderConfig(model=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
    prompts_manager = get_prompt_manager()
    cm = get_cluster_manager(prompts_manager, llm)
    run(llm, cm, prompts_manager, "3b0b4982e53b9154", 10)

def get_prompt_manager():
    embedding_store = get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'prompt', 'all-minilm-l6-v2', 384) 
    return PromptManager(embedding_store=embedding_store)

def get_cluster_manager(prompt_manager: PromptManager, llm):
    embedding_store = get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'cluster', 'all-minilm-l6-v2', 384)
    return PromptClusterManager(embedding_store=embedding_store, items_manager=prompt_manager, llm=llm)

if __name__ == "__main__":
    main()