from sereleum.data.stores.postgres.tags.tag_store import PostgresTagStore
from domains.prompts.models import PromptTagModel, PromptTagCrossRefModel, PromptModel, PromptClusterCrossRefModel
from domains.prompts.mappers import PromptTagMapper

class PromptTagStore(PostgresTagStore):
    model = PromptTagModel
    cluster_crossref_model = PromptClusterCrossRefModel
    tag_crossref_model = PromptTagCrossRefModel
    item_model = PromptModel
    mapper = PromptTagMapper()