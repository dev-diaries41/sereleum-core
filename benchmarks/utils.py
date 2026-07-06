import tracemalloc
import time

from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore
from sereleum.providers.types import TextEmbeddingModel
from sereleum.data.prompts import PromptStore, PromptClusterCrossRefStore, PromptClusterStore
from sereleum.clusters.prompt_cluster_manager import PromptClusterManager
from sereleum.data.db_config import DbConfig

from llm_connect.providers.llm_provider import LLMProvider
from dataclasses import asdict

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



def get_test_prompt_embed_store(model: TextEmbeddingModel, config_dict: dict, embed_dim: int):
    class TestPromptEmbedStore(PgVectorEmbeddingStore):
        table_name = f"prompt_embeds_{model}"
    config_dict["dsn"] = None # required
    return TestPromptEmbedStore(**config_dict, dim=embed_dim)
    
def get_test_prompt_cluster_manager(db_config: DbConfig, session_maker: async_sessionmaker, embed_dim:int, model: TextEmbeddingModel, llm: LLMProvider):
    config_dict = asdict(db_config)
    prompt_store = PromptStore(session_maker)
    prompt_cluster_store = PromptClusterStore(session_maker)
    prompt_crossref_store = PromptClusterCrossRefStore(session_maker)

    ## Simpler to use connect params for embed stores
    config_dict["dsn"] = None

    class TestPromptClusterEmbedStore(PgVectorEmbeddingStore):
        table_name = f"prompt_cluster_embeds_{model}"

    prompt_embed_store = get_test_prompt_embed_store(model, **config_dict, dim=embed_dim)
    prompt_cluster_embed_store = TestPromptClusterEmbedStore(**config_dict, dim=embed_dim)
    return PromptClusterManager(
        cluster_embedding_store=prompt_cluster_embed_store,
        cluster_store=prompt_cluster_store,
        crossrefs_store=prompt_crossref_store,
        item_embedding_store=prompt_embed_store, 
        item_store=prompt_store,
        llm=llm,
    )