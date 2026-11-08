from sereleum.data.stores.postgres.tags.tag_crossrefs_store import PostgresTagCrossRefStore
from domains.prompts.models.tags.tag_crossref import PromptTagCrossRefModel
from domains.prompts.mappers import PromptTagCrossRefMapper

class PromptTagCrossRefStore( PostgresTagCrossRefStore):
    model = PromptTagCrossRefModel
    mapper = PromptTagCrossRefMapper()