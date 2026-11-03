from sqlalchemy import exists, select

from sereleum.data.types import Filter
from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore

from domains.prompts.models.item import PromptModel
from domains.prompts.models.clusters.cluster_crossref import PromptClusterCrossRefModel
from domains.prompts.item import Prompt
from domains.prompts.mappers import PromptMapper


class PromptStore(BasePostgresStore[PromptModel, Prompt]):
    model = PromptModel
    mapper = PromptMapper()

    def apply_filters(self, stmt, f: Filter | None):
        if not f:
            return stmt

        if (ids := f.get('ids')) is not None:
            stmt = stmt.where(self.model.id.in_(ids))
        
        if (cluster_ids := f.get('cluster_ids')) is not None:
            stmt = stmt.where(
                exists(
                    select(1).where(
                        PromptClusterCrossRefModel.item_id == self.model.id,
                        PromptClusterCrossRefModel.cluster_id.in_(cluster_ids),
                    )
                )
            )

        if (min_tokens := f.get('min_tokens')) is not None:
            stmt = stmt.where(self.model >= min_tokens)

        if (max_tokens := f.get('max_tokens')) is not None:
            stmt = stmt.where(self.model.tokens <= max_tokens)

        if (created_after := f.get('created_after')) is not None:
            stmt = stmt.where(self.model.created_at >= created_after)

        if (created_before := f.get('created_before')) is not None:
            stmt = stmt.where(self.model.created_at <= created_before)

        if (updated_after := f.get('updated_after')) is not None:
            stmt = stmt.where(self.model.updated_at >= updated_after)

        if (updated_before := f.get('updated_before')) is not None:
            stmt = stmt.where(self.model.updated_at <= updated_before)

        return stmt
    