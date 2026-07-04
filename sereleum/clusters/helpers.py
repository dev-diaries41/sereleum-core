from sereleum.data.prompts.prompt_store import PromptStore
from sereleum.data.prompts.prompt_cluster_store import PromptClusterStore
from sereleum.data.prompts.prompt_cluster_crossrefs_store import PromptClusterCrossRefsStore
from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore
from sereleum.clusters.prompt_cluster_manager import PromptClusterManager
from sereleum.data.db_config import DbConfig

from llm_connect.providers.llm_provider import LLMProvider
from dataclasses import asdict

def get_prompt_cluster_manager(db_config: DbConfig, embed_dim:int, llm: LLMProvider):
    config_dict = asdict(db_config)
    prompt_store = PromptStore(**config_dict)
    prompt_cluster_store = PromptClusterStore(**config_dict)
    prompt_crossref_store = PromptClusterCrossRefsStore(**config_dict)
    prompt_embed_store = PgVectorEmbeddingStore(**config_dict, dim=embed_dim)
    prompt_cluster_embed_store = PgVectorEmbeddingStore(**config_dict, dim=embed_dim)
    return PromptClusterManager(
        cluster_embedding_store=prompt_cluster_embed_store,
        cluster_store=prompt_cluster_store,
        crossrefs_store=prompt_crossref_store,
        item_embedding_store=prompt_embed_store, 
        item_store=prompt_store,
        llm=llm,
    )