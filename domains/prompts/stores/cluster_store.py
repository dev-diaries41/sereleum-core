from sereleum.data.stores.postgres.cluster_store import PostgresClusterStore
from domains.prompts.models import PromptClusterModel, PromptClusterCrossRefModel, PromptModel
from domains.prompts.mappers import PromptClusterMapper

class PromptClusterStore(PostgresClusterStore[PromptClusterModel, PromptClusterCrossRefModel, PromptModel]):
    model = PromptClusterModel
    crossref_model = PromptClusterCrossRefModel
    item_model = PromptModel
    mapper = PromptClusterMapper()