from __future__ import annotations

import asyncio
import asyncpg

from abc import abstractmethod
from typing import Generic, List, Optional
from sereleum.data.entity import Entity
from sereleum.data.types import TItem, TItemFilter
from sereleum.data.sql_builder import build_create_table_sql

class BaseStore(Generic[TItem, TItemFilter]):
    def __init__(
        self,
        entity: Entity[TItem],
        dsn: Optional[str] = None,
        host: Optional[str] = None,
        user: Optional[str] = None,
        port: int = 5432,
        password: Optional[str] = None,
        database: Optional[str] = None,
        min_pool_size: int = 1,
        max_pool_size: int = 10,
    ):
        self.entity = entity

        if dsn is None and not database:
            raise ValueError("Either dsn or database must be provided")

        self.dsn = dsn
        self._conn_params = None

        if dsn is None:
            self._conn_params = {
                "user": user,
                "password": password,
                "database": database,
                "host": host,
                "port": port,
            }

        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
        self._init_done = False

        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size



    @abstractmethod
    def add_filters(self, query: str, filter: Optional[TItemFilter] = None) -> tuple[str, list]:
        ...

    async def _init_db(self):
        if self._init_done:
            return

        if self._pool is None:
            if self.dsn:
                self._pool = await asyncpg.create_pool(
                    dsn=self.dsn,
                    min_size=self.min_pool_size,
                    max_size=self.max_pool_size,
                )
            else:
                self._pool = await asyncpg.create_pool(
                    min_size=self.min_pool_size,
                    max_size=self.max_pool_size,
                    **self._conn_params,
                )

        async with self._pool.acquire() as conn:
            await conn.execute(build_create_table_sql(self.entity))

        self._init_done = True

    async def add(self, items: List[TItem]):
        if not items:
            return

        await self._init_db()

        values = ", ".join(f"${i+1}" for i in range(len(self.entity.columns)))

        async with self._lock:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    f"""
                    INSERT INTO {self.entity.table_name}
                    ({", ".join(self.entity.columns)})
                    VALUES ({values})
                    ON CONFLICT ({self.entity.primary_key}) DO NOTHING
                    """,
                    [self.entity.serialize(i) for i in items],
                )

    async def get(
        self,
        filter: Optional[TItemFilter] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        ascending: bool = True,
    ) -> List[TItem]:
        await self._init_db()

        if order_by not in self.entity.columns:
            order_by = self.entity.primary_key

        query = f"SELECT * FROM {self.entity.table_name} WHERE TRUE"
        query, params = self.add_filters(query, filter)
        query += f" ORDER BY {order_by} {'ASC' if ascending else 'DESC'}"

        if limit is not None:
            query += f" LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
            params.extend([limit, offset])
        else:
            query += f" OFFSET ${len(params)+1}"
            params.append(offset)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self.entity.deserialize(r) for r in rows]

    async def get_by_ids(self, ids: List[str]) -> List[TItem]:
        if not ids:
            return []

        await self._init_db()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM {self.entity.table_name}
                WHERE {self.entity.primary_key} = ANY($1)
                """,
                ids,
            )

        return [self.entity.deserialize(r) for r in rows]

    async def delete(self, ids: List[str]):
        if not ids:
            return

        await self._init_db()

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                DELETE FROM {self.entity.table_name}
                WHERE {self.entity.primary_key} = ANY($1)
                """,
                ids,
            )

    async def count(self, filter: Optional[TItemFilter] = None) -> int:
        await self._init_db()

        query = f"SELECT COUNT(*) AS count FROM {self.entity.table_name} WHERE TRUE"
        query, params = self.add_filters(query, filter)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return row["count"]

    async def upsert(self, items: list[TItem]):
        if not items:
            return

        await self._init_db()

        placeholders = ", ".join(f"${i + 1}" for i in range(len(self.entity.columns)))
        non_primary_keys = [c for c in self.entity.columns if c != self.entity.primary_key]

        updates = ", ".join(
            f"{c} = EXCLUDED.{c}"
            for c in non_primary_keys
        )

        async with self._lock:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    f"""
                    INSERT INTO {self.entity.table_name}
                    ({", ".join(self.entity.columns)})
                    VALUES ({placeholders})
                    ON CONFLICT ({self.entity.primary_key})
                    DO UPDATE SET {updates}
                    """,
                    [self.entity.serialize(i) for i in items],
                )

    async def update(self, items: list[TItem]):
        if not items:
            return

        await self._init_db()

        non_primary_keys = [c for c in self.entity.columns if c != self.entity.primary_key]

        assignments = ", ".join(
            f"{c} = ${i + 2}"
            for i, c in enumerate(non_primary_keys)
        )

        async with self._lock:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    f"""
                    UPDATE {self.entity.table_name}
                    SET {assignments}
                    WHERE {self.entity.primary_key} = $1
                    """,
                    [self.entity.serialize(item) for item in items],
                )