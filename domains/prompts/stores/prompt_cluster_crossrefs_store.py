from sereleum.data.clusters.base_cluster_crossrefs_store import BaseClusterCrossRefStore
from domains.prompts.models.prompt_cluster_crossref import PromptClusterCrossRefModel
from domains.prompts.mappers import PromptClusterCrossRefMapper

class PromptClusterCrossRefStore( BaseClusterCrossRefStore[PromptClusterCrossRefModel]):
    model = PromptClusterCrossRefModel
    mapper = PromptClusterCrossRefMapper()