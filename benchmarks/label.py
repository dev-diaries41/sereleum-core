
from dotenv import load_dotenv
load_dotenv()

import json
import os

from benchmarks.constants import BENCHMARK_CHROMADB_PATH, BENCHMARK_DIR
from sereleum.constants.models import DEFAULT_SYSTEM_PROMPT, OPENAI_API_KEY, DEFAULT_OPENAI_MODEL
from sereleum.providers.llm.openai import OpenAIClient
from sereleum.schemas.llm import LLMClientConfig
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.clusters_manager import PromptClustersManager
from sereleum.embeddings.helpers import get_embedding_store_persistent_file
from sereleum.prompts.prompts import get_labelling_prompt
from sereleum.schemas.llm import LLMClassificationResult
from sereleum.providers.llm.llm_client import LLMClient


BENCHMARK_OUTPUT_PATH = os.path.join(BENCHMARK_DIR, "labelling_benchmarks.jsonl")

os.makedirs(BENCHMARK_DIR, exist_ok=True)



def label_cluster(llm: LLMClient, cluster_manager: PromptClustersManager, prompts_manager: PromptsManager, cluster_id: str, sample_size: int, existing_labels: list[str]) -> LLMClassificationResult:
    clusters = cluster_manager.get_clusters(cluster_ids=[cluster_id], include=['embeddings'])
    if not clusters:
        raise ValueError("Cluster not found")
    prompts = prompts_manager.embedding_store.query(query_embeds=[clusters[cluster_id].embedding], filter={"cluster_id": cluster_id},  limit=sample_size, include=['documents'])
    print(f"Found {len(prompts.ids)} similar prompts_____________\n")
    print(prompts.ids)

    sample_prompts = [content for content in prompts.datas]
    input_prompt = get_labelling_prompt(cluster_id, existing_labels, sample_prompts)
    return  LLMClassificationResult(item_id="test", label="test label", confidence=0.8)

def run(llm: OpenAIClient, cm: PromptClustersManager, pm: PromptsManager, cluster_id: str, sample_size: int):
    result = label_cluster(llm, cm, pm, cluster_id, sample_size, [])
    print(result)
    
    with open(BENCHMARK_OUTPUT_PATH, "a") as f:
        json.dump(result.model_dump(), f, indent=1)

def main():
    llm = OpenAIClient(OPENAI_API_KEY, LLMClientConfig(model_name=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
    prompts_manager = get_prompt_manager()
    cm = get_cluster_manager(prompts_manager, llm)
    run(llm, cm, prompts_manager, "3b0b4982e53b9154", 10)

def get_prompt_manager():
    embedding_store = get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'prompt', 'all-minilm-l6-v2', 384) 
    return PromptsManager(embedding_store=embedding_store)

def get_cluster_manager(prompt_manager: PromptsManager, llm):
    embedding_store = get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'cluster', 'all-minilm-l6-v2', 384)
    return PromptClustersManager(embedding_store=embedding_store, items_manager=prompt_manager, llm=llm)

if __name__ == "__main__":
    main()