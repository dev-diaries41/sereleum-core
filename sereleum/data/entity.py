import asyncpg

from abc import ABC
from typing import Generic, Optional
from enum import Enum
from sereleum.data.types import TItem

class ForeignKeyAction(str, Enum):
    CASCADE = "CASCADE"
    RESTRICT = "RESTRICT"
    SET_NULL = "SET NULL"
    NO_ACTION = "NO ACTION"
    SET_DEFAULT = "SET DEFAULT"



class ForeignKey:
    def __init__(
        self,
        column: str,
        references: type["Entity[TItem]"],
        references_column: str,
        on_delete: ForeignKeyAction = ForeignKeyAction.CASCADE,
    ):
        if references_column not in references.model.model_fields:
            raise ValueError(
                f"{references_column} not in {references.model.__name__}"
            )

        self.column = column
        self.references = references
        self.references_column = references_column
        self.on_delete = on_delete


class Index:
    def __init__(self, columns: list[str], name: Optional[str] = None):
        self.columns = columns
        self.name = name


class Entity(ABC, Generic[TItem]):
    model: type[TItem]
    table_name: str
    primary_key: str

    @property
    def columns(self) -> list[str]:
        return list(self.model.model_fields.keys())

    @property
    def indexes(self) -> list[Index]:
        return []

    @property
    def foreign_keys(self) -> list[ForeignKey]:
        return []

    def serialize(self, item: TItem) -> tuple:
        d = item.model_dump()
        return tuple(d[c] for c in self.columns)

    def deserialize(self, row: asyncpg.Record) -> TItem:
        return self.model(**dict(row))
