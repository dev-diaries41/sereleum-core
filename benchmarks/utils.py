import tracemalloc
import time

from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore
from sereleum.providers.types import TextEmbeddingModel
from sereleum.data.prompts import PromptStore, PromptClusterCrossRefStore, PromptClusterStore
from sereleum.clusters.prompt_cluster_manager import PromptClusterManager

from llm_connect.providers.llm_provider import LLMProvider

from sqlalchemy.ext.asyncio import async_sessionmaker

def with_mem_profile(func):
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        result = func(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        print(f"Current memory usage: {current / 1024**2:.2f} MB | Peak memory usage: {peak / 1024**2:.2f} MB")
        return result
    return wrapper


def with_time(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        time_elapsed = time.perf_counter() - start
        print(f" Time elapsed: {time_elapsed:.6f} s")
        return result, time_elapsed
    return wrapper


## temp solution in prod use user selected labels
def get_true_labels(item_ids: list[str]):
        true_labels: dict[str, str] = {}
        for id in  item_ids:
            label = id.split("_")[0]
            if not label: 
                print(f"[WARNING] {id} is not a valid labelled item.")
                continue
            true_labels[id] = label
        return true_labels



def get_test_prompt_embed_store(model: TextEmbeddingModel, sessionmaker: async_sessionmaker, embed_dim: int):
    safe_model = model.replace("-", "_")
    class TestPromptEmbedStore(PgVectorEmbeddingStore):
        table_name = f"prompt_embeds_{safe_model}"
    return TestPromptEmbedStore(sessionmaker=sessionmaker, dim=embed_dim)
    
def get_test_prompt_cluster_manager(sessionmaker: async_sessionmaker, embed_dim:int, model: TextEmbeddingModel, llm: LLMProvider):
    prompt_store = PromptStore(sessionmaker)
    prompt_cluster_store = PromptClusterStore(sessionmaker)
    prompt_crossref_store = PromptClusterCrossRefStore(sessionmaker)

    safe_model = model.replace("-", "_")

    class TestPromptClusterEmbedStore(PgVectorEmbeddingStore):
        table_name = f"prompt_cluster_embeds_{safe_model}"

    prompt_embed_store = get_test_prompt_embed_store(safe_model, sessionmaker, embed_dim=embed_dim)
    prompt_cluster_embed_store = TestPromptClusterEmbedStore(sessionmaker=sessionmaker, dim=embed_dim)
    return PromptClusterManager(
        cluster_embedding_store=prompt_cluster_embed_store,
        cluster_store=prompt_cluster_store,
        crossrefs_store=prompt_crossref_store,
        item_embedding_store=prompt_embed_store, 
        item_store=prompt_store,
        llm=llm,
    )