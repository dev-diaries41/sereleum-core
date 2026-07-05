from smartscan.embeds import EmbeddingStore

from llm_connect.providers.llm_provider import LLMProvider

from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.schemas.items.prompt import PromptFilter
from sereleum.schemas.llm import LLMClassificationResult
from sereleum.data.prompts import PromptStore, PromptClusterStore, PromptClusterCrossRefStore
from sereleum.data.models import PromptClusterModel, PromptModel, PromptClusterCrossRefModel
from sereleum.schemas.cluster import ClusterCrossRefFilter
from sereleum.data.converters.prompt import cluster_to_orm, cluster_from_orm,  crossref_from_prompt_orm, crossref_to_prompt_orm


class PromptClusterManager(ClusterManager[PromptModel, PromptFilter, PromptClusterModel, PromptClusterCrossRefModel]):
    def __init__(
        self,
        cluster_embedding_store: EmbeddingStore,
        cluster_store: PromptClusterStore,
        crossrefs_store: PromptClusterCrossRefStore,
        item_embedding_store: EmbeddingStore,
        item_store: PromptStore,
        llm: LLMProvider, 
        label_confidence_threshold: float = 0.8,
        label_concurrency: int = 8,
    ):
        super().__init__(
            
            cluster_embedding_store=cluster_embedding_store,
            cluster_store=cluster_store,
            crossrefs_store=crossrefs_store,
            item_embedding_store=item_embedding_store,
            item_store=item_store,
            llm=llm,
            label_confidence_threshold=label_confidence_threshold,
            label_concurrency=label_concurrency,
        )
   
    
    async def label(self, cluster_id, sample_size) -> LLMClassificationResult:
        result = await self.cluster_embedding_store.get([cluster_id])
        if len(result) == 0:
            raise ValueError("Cluster not found")
        cluster_embed = result[0]
        
        ## Note: consider skipping this step and directly querying embed store without using the filter ids since items in the same cluster are most likely to be in topK
        crossrefs = await self.crossrefs_store.get(filter=ClusterCrossRefFilter(include_cluster_ids=[cluster_id]))
        ids = [c.item_id for c in crossrefs]
        query_result = await self.item_embedding_store.query(query_embed=cluster_embed.embedding, ids=ids, topK=sample_size)
        sample_prompts = [prompt.content for prompt in await self.item_store.get_by_ids(query_result.ids)]
        input_prompt = self._get_labelling_prompt(cluster_id, sample_prompts)
        return self.llm.generate_json(input_prompt, LLMClassificationResult)
    
    def to_cluster_orm(self, metadata):
        return cluster_to_orm(metadata)
    
    def to_crossref_orm(self, crossref):
        return crossref_to_prompt_orm(crossref)
    
    def from_cluster_orm(self, cluster_orm):
        return cluster_from_orm(cluster_orm)
    
    def from_crossref_orm(self, crossref_orm):
        return crossref_from_prompt_orm(crossref_orm)
    
    @staticmethod
    def _get_labelling_prompt(cluster_id: str, sample_prompts: list[str]) -> str:
        return f"""## ClusterId: {cluster_id}\n\n Cluster sample_prompts \n\n {sample_prompts}"""
    