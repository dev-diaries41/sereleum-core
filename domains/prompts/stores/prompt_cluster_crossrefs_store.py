from sereleum.data.stores.postgres.cluster_crossrefs_store import PostgresClusterCrossRefStore
from domains.prompts.models.prompt_cluster_crossref import PromptClusterCrossRefModel
from domains.prompts.mappers import PromptClusterCrossRefMapper

class PromptClusterCrossRefStore( PostgresClusterCrossRefStore[PromptClusterCrossRefModel]):
    model = PromptClusterCrossRefModel
    mapper = PromptClusterCrossRefMapper()