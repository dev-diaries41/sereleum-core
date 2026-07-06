from sereleum.data.prompts import PromptStore, PromptClusterCrossRefStore, PromptEmbedStore, PromptClusterEmbedStore, PromptClusterStore
from sereleum.clusters.prompt_cluster_manager import PromptClusterManager
from sereleum.data.db_config import DbConfig

from llm_connect.providers.llm_provider import LLMProvider
from dataclasses import asdict

from sqlalchemy.ext.asyncio import async_sessionmaker


def get_prompt_cluster_manager(db_config: DbConfig, session_maker: async_sessionmaker, embed_dim:int, llm: LLMProvider):
    config_dict = asdict(db_config)
    prompt_store = PromptStore(session_maker)
    prompt_cluster_store = PromptClusterStore(session_maker)
    prompt_crossref_store = PromptClusterCrossRefStore(session_maker)

    ## Simpler to use connect params for embed stores
    config_dict["dsn"] = None
    prompt_embed_store = PromptEmbedStore(**config_dict, dim=embed_dim)
    prompt_cluster_embed_store = PromptClusterEmbedStore(**config_dict, dim=embed_dim)
    return PromptClusterManager(
        cluster_embedding_store=prompt_cluster_embed_store,
        cluster_store=prompt_cluster_store,
        crossrefs_store=prompt_crossref_store,
        item_embedding_store=prompt_embed_store, 
        item_store=prompt_store,
        llm=llm,
    )