from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.providers.llm.llm_client import LLMClient
from sereleum.prompts.clusters_manager import PromptClustersManager
from sereleum.store.helpers import get_embedding_store, get_embedding_store_persistent_file
from sereleum.providers.types import TextEmbeddingModel

# TODO: pass client id to get unique collections per client
def get_prompt_manager(model: TextEmbeddingModel, embed_dim: int, path: str | None = None):
    if path:
        prompt_embedding_store = get_embedding_store_persistent_file(path, 'prompt', model, embed_dim) 
    else:
        prompt_embedding_store = get_embedding_store( 'prompt', model, embed_dim) 
    return  PromptsManager(embedding_store=prompt_embedding_store)


def get_cluster_manager(model: TextEmbeddingModel, embed_dim: int, prompt_manager: PromptsManager, llm: LLMClient, path: str | None = None):
    if path:
        cluster_embedding_store = get_embedding_store_persistent_file(path, 'cluster', model, embed_dim)
    else:
        cluster_embedding_store = get_embedding_store('cluster', model, embed_dim) 
    return PromptClustersManager(embedding_store=cluster_embedding_store, items_manager=prompt_manager, llm=llm)
