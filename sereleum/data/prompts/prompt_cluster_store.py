from sereleum.data.clusters.base_cluster_store import BaseClusterStore
from sereleum.data.prompts.prompt_cluster_entitiy import PromptClusterEntity

class PromptClusterStore(BaseClusterStore):
    def __init__(self, **kwargs):
        super().__init__(entity=PromptClusterEntity(), **kwargs)
