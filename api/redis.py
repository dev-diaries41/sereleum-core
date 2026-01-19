import os
import redis

from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

redis_client=redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    db=2
)
