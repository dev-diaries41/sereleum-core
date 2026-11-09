
import asyncio

from llm_connect.providers.llm_provider import LLMProvider
from sereleum.schemas.llm import LLMClassificationResult


class ClusterLabeller:
    def __init__(
        self,
        llm: LLMProvider,
        label_confidence_threshold: float = 0.8,
        label_concurrency: int = 8,
    ):
        self.llm = llm
        self.label_confidence_threshold = label_confidence_threshold
        self.label_concurrency = label_concurrency

    def label_cluster( self, cluster_id: str, sample_contents: list[str] ) -> LLMClassificationResult:
        input_prompt = self._get_cluster_labelling_prompt(cluster_id, sample_contents)
        return self.llm.generate_json(input_prompt, LLMClassificationResult)

    async def label_clusters( self, cluster_samples: dict[str, list[str]] ) -> dict[str, str]:
        sem = asyncio.Semaphore(self.label_concurrency)

        label_tasks = {
            cluster_id: self._label_cluster_with_sem(sem, cluster_id, samples)
            for cluster_id, samples in cluster_samples.items()
        }

        results = await asyncio.gather(*label_tasks.values(), return_exceptions=True)
        labelled_clusters: dict[str, str] = {}

        for cluster_id, result in zip(label_tasks.keys(), results):
            if isinstance(result, Exception):
                print(f"[WARNING] Error labelling {cluster_id} | Details: {result}")
                continue

            if result.confidence < self.label_confidence_threshold:
                print(
                    f"[WARNING] Cluster {cluster_id} not labelled | "
                    f"Details: Below confidence threshold: confidence={result.confidence}"
                )
                continue

            labelled_clusters[cluster_id] = result.label

        return labelled_clusters

    async def _label_cluster_with_sem( self, semaphore: asyncio.Semaphore, cluster_id: str, samples: list[str], ) -> LLMClassificationResult:
        async with semaphore:
            return await asyncio.to_thread(self.label_cluster, cluster_id, samples)

    @staticmethod
    def _get_cluster_labelling_prompt( cluster_id: str, sample_contents: list[str] ) -> str:
        return f"""## ClusterId: {cluster_id}

            Cluster sample items:

            {sample_contents}"""
