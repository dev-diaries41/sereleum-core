import asyncio
from typing import List, Optional

from numpy.typing import NDArray
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Index, MetaData, String, Table, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from smartscan.embeds.embedding_store import EmbeddingStore
from smartscan.embeds.types import QueryResult, StoredEmbedding


class PgVectorEmbeddingStore(EmbeddingStore):
    table_name: str

    def __init__(
        self,
        dim: int,
        sessionmaker: async_sessionmaker[AsyncSession],
        hnsw_m: int = 16,
        hnsw_ef_construction: int = 64,
    ):
        self.dim = dim
        self.sessionmaker = sessionmaker
        self.hnsw_m = hnsw_m
        self.hnsw_ef_construction = hnsw_ef_construction

        self._metadata = MetaData()
        self._table = Table(
            self.table_name,
            self._metadata,
            Column("item_id", String, primary_key=True, nullable=False),
            Column("embedding", Vector(dim), nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Index(
                f"{self.table_name}_embedding_hnsw_idx",
                "embedding",
                postgresql_using="hnsw",
                postgresql_with={
                    "m": hnsw_m,
                    "ef_construction": hnsw_ef_construction,
                },
                postgresql_ops={"embedding": "vector_cosine_ops"},
            ),
        )

        self._init_done = False
        self._init_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    @property
    def _engine(self) -> AsyncEngine:
        bind = self.sessionmaker.kw.get("bind")

        if not isinstance(bind, AsyncEngine):
            raise RuntimeError(
                "PgVectorEmbeddingStore requires an async_sessionmaker "
                "bound to an AsyncEngine"
            )

        return bind

    async def _init(self) -> None:
        if self._init_done:
            return

        async with self._init_lock:
            if self._init_done:
                return

            async with self._engine.begin() as conn:
                await conn.run_sync(self._metadata.create_all)

            self._init_done = True

    def _to_list(self, emb: NDArray) -> List[float]:
        return emb.tolist() if hasattr(emb, "tolist") else list(emb)

    async def add(self, items: List[StoredEmbedding]) -> None:
        await self._init()

        if not items:
            return

        async with self._write_lock:
            async with self.sessionmaker() as session:
                stmt = insert(self._table).values(
                    [
                        {
                            "item_id": item.item_id,
                            "embedding": self._to_list(item.embedding),
                            "created_at": item.created_at,
                        }
                        for item in items
                    ]
                ).on_conflict_do_nothing(
                    index_elements=[self._table.c.item_id]
                )

                await session.execute(stmt)
                await session.commit()

    async def get(
        self,
        ids: Optional[List[str]] = None,
    ) -> List[StoredEmbedding]:
        await self._init()

        async with self.sessionmaker() as session:
            stmt = select(
                self._table.c.item_id,
                self._table.c.embedding,
                self._table.c.created_at,
            )

            if ids:
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

        stmt = select(
            self._table.c.item_id,
            distance,
        )

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
        await self._init()

        if not items:
            return

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
        await self._init()

        if not items:
            return

        async with self._write_lock:
            async with self.sessionmaker() as session:
                stmt = insert(self._table).values(
                    [
                        {
                            "item_id": item.item_id,
                            "embedding": self._to_list(item.embedding),
                            "created_at": item.created_at,
                        }
                        for item in items
                    ]
                )

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
            stmt = delete(self._table).where(
                self._table.c.item_id.in_(ids)
            )

            await session.execute(stmt)
            await session.commit()

    async def count(self) -> int:
        await self._init()

        async with self.sessionmaker() as session:
            stmt = select(func.count()).select_from(self._table)
            result = await session.execute(stmt)
            return result.scalar_one()