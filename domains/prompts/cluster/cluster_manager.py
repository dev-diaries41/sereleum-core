from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.schemas.llm import LLMClassificationResult
from sereleum.schemas.cluster import ClusterCrossRefFilter
from domains.prompts.prompt import PromptFilter, Prompt


class PromptClusterManager(ClusterManager[Prompt]):    
    async def label(self, cluster_id, sample_size) -> LLMClassificationResult:
        result = await self.cluster_embedding_store.get([cluster_id])
        if len(result) == 0:
            raise ValueError("Cluster not found")
        cluster_embed = result[0]
        
        ## Note: consider skipping this step and directly querying embed store without using the filter ids since items in the same cluster are most likely to be in topK
        crossrefs = await self.crossrefs_store.get(filter=ClusterCrossRefFilter(include_cluster_ids=[cluster_id]))
        ids = [c.item_id for c in crossrefs]
        query_result = await self.item_embedding_store.query(query_embed=cluster_embed.embedding, ids=ids, topK=sample_size)
        sample_prompts = [prompt.content for prompt in await self.item_store.get(filter=PromptFilter(ids=query_result.ids))]
        input_prompt = self._get_labelling_prompt(cluster_id, sample_prompts)
        return self.llm.generate_json(input_prompt, LLMClassificationResult)
    
    
    @staticmethod
    def _get_labelling_prompt(cluster_id: str, sample_prompts: list[str]) -> str:
        return f"""## ClusterId: {cluster_id}\n\n Cluster sample_prompts \n\n {sample_prompts}"""
    