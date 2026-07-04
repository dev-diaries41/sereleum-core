from sereleum.clusters.prompt_cluster_manager import PromptClusterManager
from sereleum.schemas.items.prompt import PromptsOverviewInfo, PromptFilter
from smartscan import ClusterId

async def get_prompts_overview(cluster_manager: PromptClusterManager, top_n: int = 6) -> PromptsOverviewInfo:
        prompt_count = await cluster_manager.item_store.count()
        cluster_count = await cluster_manager.cluster_store.count()
        top_clusters = await cluster_manager.get_top_clusters(top_n)

        token_counts: dict[ClusterId, int] = {}
        for metadata in top_clusters:
            avg_tokens = await calculate_avg_tokens_for_cluster(cluster_manager, metadata.id, 1000)
            token_counts[metadata.id] = avg_tokens
        return PromptsOverviewInfo(total_prompts=prompt_count, total_clusters=cluster_count, top_cluster_token_counts=token_counts, top_clusters=top_clusters)


## TODO: do at db level
async def calculate_avg_tokens_for_cluster(cluster_manager: PromptClusterManager, cluster_id: str, sample_size: int) -> int:
    total_tokens = 0
    prompts_count = 0

    for prompts in await cluster_manager.item_store.get(filter=PromptFilter(cluster_ids=[cluster_id])):
        if prompts_count >= sample_size:
            break
        total_tokens += (prompts.tokens or 0)
        prompts_count += (1 if prompts.tokens else 0)
    return int(total_tokens / max(1, prompts_count))
