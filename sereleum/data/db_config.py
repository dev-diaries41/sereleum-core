import os

from dataclasses import dataclass
from typing import Optional

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
    POSTGRES_HOST=os.environ.get("POSTGRES_HOST")
    POSTGRES_USER=os.environ.get("POSTGRES_USER")
    POSTGRES_PASSWORD=os.environ.get("POSTGRES_PASSWORD")
    POSTGRES_DB=os.environ.get("POSTGRES_DB")
    
    return DbConfig(
        host=POSTGRES_HOST,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB
    )
