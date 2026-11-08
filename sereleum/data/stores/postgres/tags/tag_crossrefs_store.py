from abc import ABC

from sqlalchemy import Select

from sereleum.data.stores.postgres.base_postgres_store import BasePostgresStore
from sereleum.schemas.tag import TagCrossRef
from sereleum.data.types import Filter
from sereleum.data.models import TagCrossRefBase


class PostgresTagCrossRefStore(
    BasePostgresStore[TagCrossRefBase, TagCrossRef],
    ABC,
):

    def apply_filters(
        self,
        stmt: Select,
        f: Filter | None,
    ) -> Select:
        if not f:
            return stmt

        if (include_tag_ids := f.get('include_tag_ids')) is not None:
            stmt = stmt.where(self.model.tag_id.in_(include_tag_ids))

        if (exclude_tag_ids := f.get('exclude_tag_ids')) is not None:
            stmt = stmt.where( ~self.model.tag_id.in_(exclude_tag_ids) )
        return stmt