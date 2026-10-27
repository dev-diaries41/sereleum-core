from sereleum.data.clusters.base_cluster_store import BaseClusterStore
from sereleum.data.models.prompt_cluster import PromptClusterModel
from sereleum.data.mappers.prompt import PromptClusterMapper

class PromptClusterStore(BaseClusterStore[PromptClusterModel]):
    model = PromptClusterModel
    mapper = PromptClusterMapper()