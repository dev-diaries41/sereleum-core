import chromadb

from llm_connect.providers.llm_provider import LLMProvider

from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.clusters_manager import PromptClustersManager
from sereleum.store.chroma_store import ChromaDBEmbeddingStore
from sereleum.providers.types import TextEmbeddingModel


# TODO: pass client id to get unique collections per client
def get_prompt_manager(client: chromadb.ClientAPI, model: TextEmbeddingModel, embed_dim: int):
    collection_name = get_embedding_collection_name("prompt", model, embed_dim)
    embedding_store = ChromaDBEmbeddingStore(client.get_or_create_collection(collection_name))
    return PromptsManager(embedding_store=embedding_store)

def get_cluster_manager(client: chromadb.ClientAPI, model: TextEmbeddingModel, embed_dim: int, prompt_manager: PromptsManager, llm: LLMProvider):
    collection_name = get_embedding_collection_name("cluster", model, embed_dim)
    embedding_store = ChromaDBEmbeddingStore(client.get_or_create_collection(collection_name))
    return PromptClustersManager(embedding_store=embedding_store, items_manager=prompt_manager, llm=llm)

def get_embedding_collection_name( type: str, model: TextEmbeddingModel, embed_dim: int) -> str:
    return f"{type}_{model}_{embed_dim}_collection"

