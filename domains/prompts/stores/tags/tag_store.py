from sereleum.data.stores.postgres.tags.tag_store import PostgresTagStore
from domains.prompts.models import PromptTagModel, PromptTagCrossRefModel, PromptModel
from domains.prompts.mappers import PromptTagMapper

class PromptTagStore(PostgresTagStore[PromptTagModel, PromptTagCrossRefModel, PromptModel]):
    model = PromptTagModel
    crossref_model = PromptTagCrossRefModel
    item_model = PromptModel
    mapper = PromptTagMapper()