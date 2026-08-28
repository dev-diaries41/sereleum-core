from dataclasses import dataclass
from typing import Optional

from sereleum.constants.db import POSTGRES_DB, POSTGRES_DSN, POSTGRES_HOST, POSTGRES_PASSWORD, POSTGRES_USER

@dataclass(frozen=True)
class DbConfig:
    dsn: Optional[str] = None
    host: Optional[str] = None
    user: Optional[str] = None
    port: int = 5432
    password: Optional[str] = None
    database: Optional[str] = None
    min_pool_size: int = 1
    max_pool_size: int = 10

def get_config(): 
    return DbConfig(
        dsn=POSTGRES_DSN,
        host=POSTGRES_HOST,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB
    )
