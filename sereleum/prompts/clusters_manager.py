from smartscan.embeds import EmbeddingStore

from sereleum.store.clusters_manager import ClustersManager
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.types import Prompt, PromptMetadata
from llm_connect.providers.llm_provider import LLMProvider
from sereleum.schemas.llm import LLMClassificationResult
from sereleum.prompts.prompts import get_labelling_prompt

class PromptClustersManager(ClustersManager[Prompt, str, PromptMetadata]):
    def __init__(
        self,
        embedding_store: EmbeddingStore,
        items_manager: PromptsManager,
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
        input_prompt = get_labelling_prompt(cluster_id, existing_labels, sample_prompts)
        return self.llm.generate_json(input_prompt, LLMClassificationResult)
        