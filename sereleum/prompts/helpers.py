from sereleum.prompts.clusters_manager import PromptClustersManager
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.types import PromptsOverviewInfo
from smartscan import ClusterId

def get_prompts_overview(prompt_manager: PromptsManager, cluster_manager: PromptClustersManager, top_n: int = 6) -> PromptsOverviewInfo:
        prompt_count = prompt_manager.embedding_store.count()
        cluster_count = cluster_manager.embedding_store.count()
        top_clusters = cluster_manager.get_top_clusters(top_n)

        token_counts: dict[ClusterId, int] = {}
        for cluster_id in top_clusters.keys():
            avg_tokens = cluster_manager.calculate_avg_tokens_for_cluster(cluster_id, 1000)
            token_counts[cluster_id] = avg_tokens
        return PromptsOverviewInfo(total_prompts=prompt_count, total_clusters=cluster_count, top_cluster_token_counts=token_counts, top_clusters=top_clusters.values())

