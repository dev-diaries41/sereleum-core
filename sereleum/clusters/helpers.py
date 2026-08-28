from sereleum.data.prompts import PromptStore, PromptClusterCrossRefStore, PromptEmbedStore, PromptClusterEmbedStore, PromptClusterStore
from sereleum.clusters.prompt_cluster_manager import PromptClusterManager

from llm_connect.providers.llm_provider import LLMProvider

from sqlalchemy.ext.asyncio import async_sessionmaker


def get_prompt_cluster_manager(sessionmaker: async_sessionmaker, embed_dim:int, llm: LLMProvider):
    prompt_store = PromptStore(sessionmaker)
    prompt_cluster_store = PromptClusterStore(sessionmaker)
    prompt_crossref_store = PromptClusterCrossRefStore(sessionmaker)


    prompt_embed_store = PromptEmbedStore(sessionmaker=sessionmaker, dim=embed_dim)
    prompt_cluster_embed_store = PromptClusterEmbedStore(sessionmaker=sessionmaker, dim=embed_dim)
    return PromptClusterManager(
        cluster_embedding_store=prompt_cluster_embed_store,
        cluster_store=prompt_cluster_store,
        crossrefs_store=prompt_crossref_store,
        item_embedding_store=prompt_embed_store, 
        item_store=prompt_store,
        llm=llm,
    )