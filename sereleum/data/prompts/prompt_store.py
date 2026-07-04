from sereleum.schemas.items.prompt import Prompt, PromptFilter
from sereleum.data.base_store import BaseStore
from typing import Optional
from sereleum.data.prompts.prompt_entitiy import PromptEntity
from sereleum.data.table_names import TableNames


class PromptStore(BaseStore[Prompt, PromptFilter]):
    def __init__(self, **kwargs):
        super().__init__(entity=PromptEntity(), **kwargs)

        self._cluster_crossref_table = TableNames.PROMPT_CLUSTER_CROSSREFS.value

    def add_filters(self, query: str, f: Optional[PromptFilter] = None):
        params = []
        if not f:
            return query, params
        
        if f.cluster_ids:
            params.append(f.cluster_ids)
            query += f"""
            AND EXISTS (
                SELECT 1
                FROM {self._cluster_crossref_table} c
                WHERE c.item_id = prompts.id
                AND c.cluster_id = ANY(${len(params)})
            )
            """

        if f.min_tokens is not None:
            params.append(f.min_tokens)
            query += f" AND tokens >= ${len(params)}"

        if f.max_tokens is not None:
            params.append(f.max_tokens)
            query += f" AND tokens <= ${len(params)}"

        if f.created_after is not None:
            params.append(f.created_after)
            query += f" AND created_at >= ${len(params)}"

        if f.created_before is not None:
            params.append(f.created_before)
            query += f" AND created_at <= ${len(params)}"

        if f.updated_after is not None:
            params.append(f.updated_after)
            query += f" AND updated_at >= ${len(params)}"

        if f.updated_before is not None:
            params.append(f.updated_before)
            query += f" AND updated_at <= ${len(params)}"

        return query, params