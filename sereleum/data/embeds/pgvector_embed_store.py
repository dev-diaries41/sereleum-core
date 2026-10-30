
import asyncio
from typing import List, Optional

from numpy.typing import NDArray

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, MetaData, String, Table, delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from smartscan.embeds.embedding_store import EmbeddingStore
from smartscan.embeds.types import QueryResult, StoredEmbedding


class PgVectorEmbeddingStore(EmbeddingStore):
    def __init__(
        self,
        name: str,
        sessionmaker: async_sessionmaker[AsyncSession],
        hnsw_m: int = 16,
        hnsw_ef_construction: int = 64,
    ):
        self.table_name = name
        self.sessionmaker = sessionmaker
        self.hnsw_m = hnsw_m
        self.hnsw_ef_construction = hnsw_ef_construction

        self._metadata = MetaData()
        self._table = Table(
            self.table_name,
            self._metadata,
            Column("item_id", String, primary_key=True, nullable=False),
            Column("embedding", Vector(), nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )

        self._dim: Optional[int] = None
        self._init_done = False
        self._init_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    @property
    def _engine(self) -> AsyncEngine:
        bind = self.sessionmaker.kw.get("bind")
        if not isinstance(bind, AsyncEngine):
            raise RuntimeError("An AsyncEngine-bound async_sessionmaker is required")
        return bind

    @staticmethod
    def _to_list(emb: NDArray) -> List[float]:
        return emb.tolist() if hasattr(emb, "tolist") else list(emb)

    async def _init(self) -> None:
        async with self._init_lock:
            if self._init_done:
                return

            async with self._engine.begin() as conn:
                await conn.run_sync(self._metadata.create_all)

                self._dim = await self._get_embedding_dim(conn)

            self._init_done = True

    async def _get_embedding_dim(self, conn) -> Optional[int]:
        result = await conn.execute(
            text("""
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                WHERE a.attrelid = to_regclass(:table_name)
                AND a.attname = 'embedding'
                AND NOT a.attisdropped
            """),
            {"table_name": self.table_name},
        )
        column_type = result.scalar_one_or_none()
        if not column_type or "(" not in column_type:
            return None
        return int(column_type.split("(")[1].split(")")[0])


    async def _init_hnsw_index(self, dim: int) -> None:
        await self._init()

        async with self._init_lock:
            if self._dim is not None:
                if self._dim != dim:
                    raise ValueError(
                        f"Embedding dimension mismatch: expected {self._dim}, got {dim}"
                    )
                return

            async with self._engine.begin() as conn:
                await conn.execute(text(
                    f'ALTER TABLE "{self.table_name}" '
                    f'ALTER COLUMN embedding TYPE vector({dim})'
                ))
                await conn.execute(text(
                    f'CREATE INDEX IF NOT EXISTS "{self.table_name}_embedding_hnsw_idx" '
                    f'ON "{self.table_name}" USING hnsw '
                    f'(embedding vector_cosine_ops) '
                    f'WITH (m = {self.hnsw_m}, ef_construction = {self.hnsw_ef_construction})'
                ))

            self._dim = dim


    def _validate_items(self, items: List[StoredEmbedding]) -> None:
        if self._dim is not None:
            for item in items:
                if len(item.embedding) != self._dim:
                    raise ValueError(
                        f"Embedding dimension mismatch: expected {self._dim}, got {len(item.embedding)}"
                    )

    async def add(self, items: List[StoredEmbedding]) -> None:
        if not items:
            return

        await self._init_hnsw_index(len(items[0].embedding))
        self._validate_items(items)

        async with self._write_lock:
            async with self.sessionmaker() as session:
                stmt = insert(self._table).values([
                    {
                        "item_id": item.item_id,
                        "embedding": self._to_list(item.embedding),
                        "created_at": item.created_at,
                    }
                    for item in items
                ]).on_conflict_do_nothing(index_elements=[self._table.c.item_id])

                await session.execute(stmt)
                await session.commit()

    async def get(self, ids: Optional[List[str]] = None) -> List[StoredEmbedding]:
        await self._init()

        async with self.sessionmaker() as session:
            stmt = select(
                self._table.c.item_id,
                self._table.c.embedding,
                self._table.c.created_at,
            )

            if ids is not None:
                stmt = stmt.where(self._table.c.item_id.in_(ids))

            result = await session.execute(stmt)
            rows = result.mappings().all()

        return [
            StoredEmbedding(
                item_id=row["item_id"],
                embedding=row["embedding"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def query(
        self,
        query_embed: NDArray,
        topK: int,
        ids: Optional[List[str]] = None,
        include_sims: bool = False,
        threshold: Optional[float] = None,
    ) -> QueryResult:
        await self._init()

        distance = self._table.c.embedding.cosine_distance(
            self._to_list(query_embed)
        ).label("sim")

        stmt = select(self._table.c.item_id, distance)

        if ids is not None:
            stmt = stmt.where(self._table.c.item_id.in_(ids))

        if threshold is not None:
            stmt = stmt.where(distance <= threshold)

        stmt = stmt.order_by(distance).limit(topK)

        async with self.sessionmaker() as session:
            result = await session.execute(stmt)
            rows = result.mappings().all()

        return QueryResult(
            ids=[row["item_id"] for row in rows],
            sims=[row["sim"] for row in rows] if include_sims else None,
        )

    async def update(self, items: List[StoredEmbedding]) -> None:
        if not items:
            return

        await self._init()
        self._validate_items(items)

        async with self._write_lock:
            async with self.sessionmaker() as session:
                for item in items:
                    stmt = (
                        update(self._table)
                        .where(self._table.c.item_id == item.item_id)
                        .values(
                            embedding=self._to_list(item.embedding),
                            created_at=item.created_at,
                        )
                    )
                    await session.execute(stmt)

                await session.commit()

    async def upsert(self, items: List[StoredEmbedding]) -> None:
        if not items:
            return

        await self._init_hnsw_index(len(items[0].embedding))

        self._validate_items(items)

        async with self._write_lock:
            async with self.sessionmaker() as session:
                stmt = insert(self._table).values([
                    {
                        "item_id": item.item_id,
                        "embedding": self._to_list(item.embedding),
                        "created_at": item.created_at,
                    }
                    for item in items
                ])

                stmt = stmt.on_conflict_do_update(
                    index_elements=[self._table.c.item_id],
                    set_={
                        "embedding": stmt.excluded.embedding,
                        "created_at": stmt.excluded.created_at,
                    },
                )

                await session.execute(stmt)
                await session.commit()

    async def delete(self, ids: List[str]) -> None:
        await self._init()

        if not ids:
            return

        async with self.sessionmaker() as session:
            stmt = delete(self._table).where(self._table.c.item_id.in_(ids))
            await session.execute(stmt)
            await session.commit()

    async def count(self) -> int:
        await self._init()

        async with self.sessionmaker() as session:
            stmt = select(func.count()).select_from(self._table)
            result = await session.execute(stmt)
            return result.scalar_one()
