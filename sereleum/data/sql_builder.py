from typing import get_origin, get_args, Union

from enum import Enum
from sereleum.data.entity import Entity


class SQLType(str, Enum):
    TEXT = "TEXT"
    INT = "INT"
    REAL = "REAL"
    BOOL = "BOOLEAN"
    TIMESTAMPTZ = "TIMESTAMPTZ"


def resolve_sql_type(py_type: type) -> tuple[SQLType, bool]:
    origin = get_origin(py_type)
    args = get_args(py_type)

    if origin is Union and type(None) in args:
        inner = [a for a in args if a is not type(None)][0]
        sql_type, _ = resolve_sql_type(inner)
        return sql_type, True

    if py_type is int:
        return SQLType.INT, False
    if py_type is float:
        return SQLType.REAL, False
    if py_type is bool:
        return SQLType.BOOL, False
    if py_type is str:
        return SQLType.TEXT, False

    return SQLType.TEXT, False


def build_create_table_sql(entity: Entity) -> str:
    cols = []

    for name in entity.columns:
        field = entity.model.model_fields[name]
        sql_type, nullable = resolve_sql_type(field.annotation)

        col_def = f"{name} {sql_type.value}"

        if name == entity.primary_key:
            col_def += " PRIMARY KEY"
        elif not nullable:
            col_def += " NOT NULL"

        cols.append(col_def)

    fk_sql = [
        f"FOREIGN KEY ({fk.column}) "
        f"REFERENCES {fk.references.table_name}({fk.references_column}) "
        f"ON DELETE {fk.on_delete.value}"
        for fk in entity.foreign_keys
    ]

    table_sql = f"""
    CREATE TABLE IF NOT EXISTS {entity.table_name} (
        {", ".join(cols + fk_sql)}
    );
    """

    index_sql = []
    for idx in entity.indexes:
        name = idx.name or f"idx_{entity.table_name}_{'_'.join(idx.columns)}"
        cols = ", ".join(idx.columns)
        index_sql.append(
            f"CREATE INDEX IF NOT EXISTS {name} "
            f"ON {entity.table_name} ({cols});"
        )

    return "\n".join([table_sql] + index_sql)