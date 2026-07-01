from smartscan.embeds import EmbeddingStore

from llm_connect.providers.llm_provider import LLMProvider

from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.items.prompt_manager import PromptManager
from sereleum.schemas.items.prompt import Prompt, PromptMetadata
from sereleum.schemas.llm import LLMClassificationResult


class PromptClusterManager(ClusterManager[Prompt, str, PromptMetadata]):
    def __init__(
        self,
        embedding_store: EmbeddingStore,
        items_manager: PromptManager,
        llm: LLMProvider,
        label_confidence_threshold: float = 0.8,
        label_concurrency: int = 8,
    ):
        super().__init__(
            embedding_store=embedding_store,
            items_manager=items_manager,
            llm=llm,
            label_confidence_threshold=label_confidence_threshold,
            label_concurrency=label_concurrency,
        )
   
    
    def label(self, cluster_id, sample_size, existing_labels) -> LLMClassificationResult:
        clusters = self.get_clusters(cluster_ids=[cluster_id], include=['embeddings'])
        if not clusters:
            raise ValueError("Cluster not found")
        prompts = self.items_manager.embedding_store.query(query_embeds=[clusters[cluster_id].embedding], filter={"cluster_id": cluster_id},  limit=sample_size, include=['documents'])
        sample_prompts = [content for content in prompts.datas]
        input_prompt = self._get_labelling_prompt(cluster_id, existing_labels, sample_prompts)
        return self.llm.generate_json(input_prompt, LLMClassificationResult)
    
    @staticmethod
    def _get_labelling_prompt(cluster_id: str, existing_labels: list[str], sample_prompts: list[str]) -> str:
        return f"""## ClusterId: {cluster_id}\n\n##Existing labels {existing_labels} Cluster sample_prompts \n\n {sample_prompts}"""
    