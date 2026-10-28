from sereleum.data.clusters.base_cluster_store import BaseClusterStore
from sereleum.data.models import PromptClusterModel, PromptClusterCrossRefModel, PromptModel
from domains.prompts.mappers import PromptClusterMapper

class PromptClusterStore(BaseClusterStore[PromptClusterModel, PromptClusterCrossRefModel, PromptModel]):
    model = PromptClusterModel
    crossref_model = PromptClusterCrossRefModel
    item_model = PromptModel
    mapper = PromptClusterMapper()