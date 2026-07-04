from sereleum.schemas.items.prompt import Prompt
from sereleum.data.entity import Entity, Index
from sereleum.data.table_names import TableNames


class PromptEntity(Entity[Prompt]):
    model = Prompt
    table_name = TableNames.PROMPTS.value
    primary_key = "id"

    @property
    def indexes(self):
        return [
            Index(["tokens"]),
            Index(["created_at"]),
            Index(["updated_at"]),
        ]



