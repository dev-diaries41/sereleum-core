
from dotenv import load_dotenv
load_dotenv()

import json
import os

from benchmarks.constants import BENCHMARK_CHROMADB_PATH, BENCHMARK_DIR
from sereleum.constants.models import DEFAULT_SYSTEM_PROMPT, OPENAI_API_KEY, DEFAULT_OPENAI_MODEL
from sereleum.providers.llm.openai import OpenAIClient
from sereleum.schemas.llm import LLMClientConfig
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.clusters.clusters_manager import ClustersManager
from sereleum.clusters.label import label_prompts
from sereleum.embeddings.helpers import get_embedding_store_persistent_file

BENCHMARK_OUTPUT_PATH = os.path.join(BENCHMARK_DIR, "labelling_benchmarks.jsonl")

os.makedirs(BENCHMARK_DIR, exist_ok=True)

def run(llm: OpenAIClient, pm: PromptsManager, cluster_id: str, sample_size: int):
    result = label_prompts(llm, pm, cluster_id, sample_size, [])
    print(result)
    
    with open(BENCHMARK_OUTPUT_PATH, "a") as f:
        json.dump(result.model_dump(), f, indent=1)

def main():
    llm = OpenAIClient(OPENAI_API_KEY, LLMClientConfig(model_name=DEFAULT_OPENAI_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT))
    prompts_manager = get_prompt_manager()
    run(llm, prompts_manager, "fce4cfdc44b3ea3f", 10)

def get_prompt_manager():
    embedding_store = get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'prompt', 'all-minilm-l6-v2', 384) 
    return PromptsManager(embedding_store=embedding_store)

def get_cluster_manager(prompt_manager: PromptsManager, llm):
    embedding_store = get_embedding_store_persistent_file(BENCHMARK_CHROMADB_PATH, 'cluster', 'all-minilm-l6-v2', 384)
    return ClustersManager(embedding_store=embedding_store, prompts_manager=prompt_manager, llm=llm)

if __name__ == "__main__":
    main()