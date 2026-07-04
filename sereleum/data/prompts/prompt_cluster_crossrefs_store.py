from sereleum.data.clusters.base_cluster_crossrefs_store import BaseClusterCrossRefStore
from sereleum.data.prompts.prompt_cluster_crossref_entity import PromptClusterCrossRefEntity

class PromptClusterCrossRefsStore(BaseClusterCrossRefStore):
    def __init__(self, **kwargs):
        super().__init__(entity=PromptClusterCrossRefEntity(), **kwargs)