from sereleum.clusters.clusters_manager import ClustersManager
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.providers.llm.llm_client import LLMClient
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.clusters.clusters_manager import ClustersManager
from sereleum.embeddings.helpers import get_embedding_store
from sereleum.providers.types import TextEmbeddingModel

# TODO: pass client id to get unique collections per client
def get_prompt_manager(embedding_model: TextEmbeddingModel, embed_dim: int):
    prompt_embedding_store = get_embedding_store( 'prompt', embedding_model, embed_dim) 
    return  PromptsManager(embedding_store=prompt_embedding_store)


def get_cluster_manager(embedding_model: TextEmbeddingModel, embed_dim: int, prompt_manager: PromptsManager, llm: LLMClient):
    cluster_embedding_store = get_embedding_store('cluster', embedding_model, embed_dim) 
    return  ClustersManager(embedding_store=cluster_embedding_store, prompts_manager=prompt_manager, llm=llm)
