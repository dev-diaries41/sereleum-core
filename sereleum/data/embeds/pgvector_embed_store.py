import asyncpg
import asyncio

from typing import List, Optional
from numpy.typing import NDArray

from smartscan.embeds.types import StoredEmbedding, QueryResult
from smartscan.embeds.embedding_store import EmbeddingStore

from pgvector.asyncpg import register_vector

class PgVectorEmbeddingStore(EmbeddingStore):
    def __init__(
        self,
        dim: int,
        dsn: Optional[str] = None,
        host: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        port: int = 5432,
        min_pool_size: int = 1,
        max_pool_size: int = 10,
    ):
        self.dim = dim
        self.dsn = dsn
        self._conn_params = None

        if dsn is None:
            self._conn_params = dict(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port,
            )

        self._pool: Optional[asyncpg.pool.Pool] = None
        self._init_done = False
        self._lock = asyncio.Lock()

        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size

    async def _init(self):
        if self._init_done:
            return

        conn = await asyncpg.connect(**(self._conn_params or {"dsn": self.dsn}))

        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS embeddings (
                    item_id TEXT PRIMARY KEY,
                    embedding VECTOR({self.dim}) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
            """)
        finally:
            await conn.close()


        if self._pool is None:
            if self.dsn:
                self._pool = await asyncpg.create_pool(
                    dsn=self.dsn,
                    min_size=self.min_pool_size,
                    max_size=self.max_pool_size,
                    init=self._init_conn,
                )
            else:
                self._pool = await asyncpg.create_pool(
                    min_size=self.min_pool_size,
                    max_size=self.max_pool_size,
                    init=self._init_conn,
                    **self._conn_params,
                )

        self._init_done = True

    async def _init_conn(self, conn):
        await register_vector(conn)

    def _to_list(self, emb: NDArray) -> List[float]:
        return emb.tolist() if hasattr(emb, "tolist") else list(emb)

    async def add(self, items: List[StoredEmbedding]) -> None:
        await self._init()
        if not items:
            return

        async with self._lock:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO embeddings (item_id, embedding, created_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (item_id) DO NOTHING
                    """,
                    [
                        (i.item_id, self._to_list(i.embedding), i.created_at)
                        for i in items
                    ],
                )

    async def get(self, ids: Optional[List[str]] = None) -> List[StoredEmbedding]:
        await self._init()

        async with self._pool.acquire() as conn:
            if ids:
                rows = await conn.fetch(
                    f"""
                    SELECT item_id, embedding, created_at
                    FROM embeddings
                    WHERE item_id = ANY($1)
                    """,
                    ids,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT item_id, embedding, created_at
                    FROM embeddings
                    """
                )

        return [
            StoredEmbedding(
                item_id=r["item_id"],
                embedding=r["embedding"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def query(
        self,
        query_embed: NDArray,
        topK: int,
        ids: Optional[List[str]] = None,
        include_sims: bool = False,
    ) -> QueryResult:
        await self._init()

        params: List = [self._to_list(query_embed), topK]
        where = ""

        if ids:
            params.append(ids)
            where = "WHERE item_id = ANY($3)"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT item_id,
                       embedding <=> $1 AS sim
                FROM embeddings
                {where}
                ORDER BY embedding <=> $1
                LIMIT $2
                """,
                *params,
            )

        return QueryResult(
            ids=[r["item_id"] for r in rows],
            sims=[r["sim"] for r in rows] if include_sims else None,
        )

    async def update(self, items: List[StoredEmbedding]) -> None:
        await self._init()
        if not items:
            return

        async with self._lock:
            async with self._pool.acquire() as conn:
                for i in items:
                    await conn.execute(
                        """
                        UPDATE embeddings
                        SET embedding = $2,
                            created_at = $3
                        WHERE item_id = $1
                        """,
                        i.item_id,
                        self._to_list(i.embedding),
                        i.created_at,
                    )

    async def upsert(self, items: List[StoredEmbedding]) -> None:
        await self._init()
        if not items:
            return

        async with self._lock:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO embeddings (item_id, embedding, created_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (item_id)
                    DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        created_at = EXCLUDED.created_at
                    """,
                    [
                        (i.item_id, self._to_list(i.embedding), i.created_at)
                        for i in items
                    ],
                )

    async def delete(self, ids: List[str]) -> None:
        await self._init()
        if not ids:
            return

        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM embeddings WHERE item_id = ANY($1)",
                ids,
            )

    async def count(self) -> int:
        await self._init()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT COUNT(*) AS c FROM embeddings")
            return row["c"]