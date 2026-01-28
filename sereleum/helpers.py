from sereleum.clusters.clusters_manager import ClustersManager
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.providers.llm.llm_client import LLMClient
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.clusters.clusters_manager import ClustersManager
from sereleum.embeddings.helpers import get_embedding_store
from sereleum.types import PromptsOverviewInfo
from sereleum.providers.types import TextEmbeddingModel

from typing import Iterator, Callable, TypeVar
from smartscan import ClusterId

def get_prompts_overview(prompt_manager: PromptsManager, cluster_manager: ClustersManager) -> PromptsOverviewInfo:
        prompt_count = prompt_manager.embedding_store.count()
        cluster_count = cluster_manager.embedding_store.count()
        top_clusters = cluster_manager.get_top_clusters(5)

        token_counts: dict[ClusterId, int] = {}
        for cluster_id in top_clusters.keys():
            avg_tokens = cluster_manager.calculate_avg_tokens_for_cluster(cluster_id, 1000)
            token_counts[cluster_id] = avg_tokens
        return PromptsOverviewInfo(total_prompts=prompt_count, total_clusters=cluster_count, top_cluster_token_counts=token_counts, top_clusters=top_clusters.values())


# TODO: pass client id to get unique collections per client
def get_prompt_manager(embedding_model: TextEmbeddingModel, embed_dim: int):
    prompt_embedding_store = get_embedding_store( 'prompt', embedding_model, embed_dim) 
    return  PromptsManager(embedding_store=prompt_embedding_store)


def get_cluster_manager(embedding_model: TextEmbeddingModel, embed_dim: int, prompt_manager: PromptsManager, llm: LLMClient):
    cluster_embedding_store = get_embedding_store('cluster', embedding_model, embed_dim) 
    return  ClustersManager(embedding_store=cluster_embedding_store, prompts_manager=prompt_manager, llm=llm)


T = TypeVar("T")

def paginate_until_total(fetch_fn: Callable[[int, int], T], total: int, batch_size: int = 500, initial_offset: int = 0) -> Iterator[T]:
    offset = initial_offset
    while offset < total:
        yield fetch_fn(offset, batch_size)
        offset += batch_size

def paginate_until(fetch_fn: Callable[[int, int], T], break_fn: Callable[[T], bool], batch_size: int = 500, initial_offset: int = 0) -> Iterator[T]:
    offset = initial_offset
    while True:
        batch = fetch_fn(offset, batch_size)
        if break_fn(batch):
            break
        yield batch
        offset += batch_size