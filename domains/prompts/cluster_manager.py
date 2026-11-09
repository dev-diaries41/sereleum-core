from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore
from sereleum.label.cluster_labeller import ClusterLabeller

from domains.prompts.item import Prompt
from domains.prompts.stores import PromptStore, PromptClusterCrossRefStore, PromptClusterStore

from sqlalchemy.ext.asyncio import async_sessionmaker

from llm_connect.providers.llm_provider import LLMProvider

def create_cluster_manager(
        sessionmaker: async_sessionmaker, 
        llm: LLMProvider,
        collection_name: str = 'prompts'
        ):
    labeller = ClusterLabeller(llm=llm)
    item_store = PromptStore(sessionmaker)
    cluster_store = PromptClusterStore(sessionmaker)
    cluster_crossref_store = PromptClusterCrossRefStore(sessionmaker)
    item_embed_store = PgVectorEmbeddingStore(name=f'{collection_name}_embeds', sessionmaker=sessionmaker)
    cluster_embed_store = PgVectorEmbeddingStore(name=f'{collection_name}_embeds', sessionmaker=sessionmaker)
    return ClusterManager[Prompt](
        cluster_embedding_store=cluster_embed_store,
        cluster_store=cluster_store,
        crossrefs_store=cluster_crossref_store,
        item_embedding_store=item_embed_store, 
        item_store=item_store,
        labeller=labeller,
    )