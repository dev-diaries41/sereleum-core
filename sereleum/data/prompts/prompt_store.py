from sqlalchemy import exists, select

from sereleum.data.base_store import BaseStore
from sereleum.data.models.prompt import PromptModel
from sereleum.data.models.prompt_cluster_crossref import PromptClusterCrossRefModel
from sereleum.schemas.items.prompt import PromptFilter


class PromptStore(BaseStore[PromptModel, PromptFilter]):
    model = PromptModel
    primary_key = "id"

    def apply_filters(self, stmt, f: PromptFilter | None):
        if not f:
            return stmt

        if f.cluster_ids:
            stmt = stmt.where(
                exists(
                    select(1).where(
                        PromptClusterCrossRefModel.item_id == PromptModel.id,
                        PromptClusterCrossRefModel.cluster_id.in_(f.cluster_ids),
                    )
                )
            )

        if f.min_tokens is not None:
            stmt = stmt.where(PromptModel.tokens >= f.min_tokens)

        if f.max_tokens is not None:
            stmt = stmt.where(PromptModel.tokens <= f.max_tokens)

        if f.created_after is not None:
            stmt = stmt.where(PromptModel.created_at >= f.created_after)

        if f.created_before is not None:
            stmt = stmt.where(PromptModel.created_at <= f.created_before)

        if f.updated_after is not None:
            stmt = stmt.where(PromptModel.updated_at >= f.updated_after)

        if f.updated_before is not None:
            stmt = stmt.where(PromptModel.updated_at <= f.updated_before)

        return stmt