from sqlalchemy import exists, select

from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from domains.prompts.models.prompt import PromptModel
from domains.prompts.models.prompt_cluster_crossref import PromptClusterCrossRefModel
from domains.prompts.prompt import PromptFilter, Prompt
from domains.prompts.mappers import PromptMapper


class PromptStore(BasePostgresStore[PromptModel, Prompt]):
    model = PromptModel
    mapper = PromptMapper()

    def apply_filters(self, stmt, f: PromptFilter | None):
        if not f:
            return stmt

        if f.ids:
            stmt = stmt.where(self.model.id.in_(f.ids))

        if f.cluster_ids:
            stmt = stmt.where(
                exists(
                    select(1).where(
                        PromptClusterCrossRefModel.item_id == self.model.id,
                        PromptClusterCrossRefModel.cluster_id.in_(f.cluster_ids),
                    )
                )
            )

        if f.min_tokens is not None:
            stmt = stmt.where(self.model >= f.min_tokens)

        if f.max_tokens is not None:
            stmt = stmt.where(self.model.tokens <= f.max_tokens)

        if f.created_after is not None:
            stmt = stmt.where(self.model.created_at >= f.created_after)

        if f.created_before is not None:
            stmt = stmt.where(self.model.created_at <= f.created_before)

        if f.updated_after is not None:
            stmt = stmt.where(self.model.updated_at >= f.updated_after)

        if f.updated_before is not None:
            stmt = stmt.where(self.model.updated_at <= f.updated_before)

        return stmt
    