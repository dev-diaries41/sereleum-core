from sereleum.data.clusters.base_cluster_crossrefs_store import BaseClusterCrossRefStore
from sereleum.data.models.prompt_cluster_crossref import PromptClusterCrossRefModel
from sereleum.data.mappers.prompt import PromptClusterCrossRefMapper

class PromptClusterCrossRefStore( BaseClusterCrossRefStore[PromptClusterCrossRefModel]):
    model = PromptClusterCrossRefModel
    mapper = PromptClusterCrossRefMapper()