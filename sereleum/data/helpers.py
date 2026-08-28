from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def create_sessionmaker(
    dsn: str,
    hnsw_ef_search: int = 100,
) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(dsn, echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_connection, connection_record):
        dbapi_connection.run_async(
            lambda conn: conn.execute(
                f"SET hnsw.ef_search = {int(hnsw_ef_search)}"
            )
        )

    return async_sessionmaker(
        engine,
        expire_on_commit=False,
    )