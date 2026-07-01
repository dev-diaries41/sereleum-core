from sereleum.clusters.prompt_cluster_manager import PromptClusterManager
from sereleum.items.prompt_manager import PromptManager
from sereleum.types import PromptsOverviewInfo
from smartscan import ClusterId

def get_prompts_overview(prompt_manager: PromptManager, cluster_manager: PromptClusterManager, top_n: int = 6) -> PromptsOverviewInfo:
        prompt_count = prompt_manager.embedding_store.count()
        cluster_count = cluster_manager.embedding_store.count()
        top_clusters = cluster_manager.get_top_clusters(top_n)

        token_counts: dict[ClusterId, int] = {}
        for cluster_id in top_clusters.keys():
            avg_tokens = calculate_avg_tokens_for_cluster(prompt_manager, cluster_id, 1000)
            token_counts[cluster_id] = avg_tokens
        return PromptsOverviewInfo(total_prompts=prompt_count, total_clusters=cluster_count, top_cluster_token_counts=token_counts, top_clusters=top_clusters.values())


def calculate_avg_tokens_for_cluster(prompts_manager: PromptManager, cluster_id: str, sample_size: int) -> int:
    total_tokens = 0
    prompts_count = 0

    for _, metadata in prompts_manager.stream_metadata([cluster_id]):
        if prompts_count >= sample_size:
            break
        total_tokens += (metadata.tokens or 0)
        prompts_count += (1 if metadata.tokens else 0)
    return int(total_tokens / max(1, prompts_count))
