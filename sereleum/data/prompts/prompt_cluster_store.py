from sereleum.data.clusters.base_cluster_store import BaseClusterStore
from sereleum.data.models.prompt_cluster import PromptClusterModel

class PromptClusterStore(BaseClusterStore[PromptClusterModel]):
    model = PromptClusterModel
    primary_key = "id"