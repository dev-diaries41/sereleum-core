import redis
import redis.asyncio

from dramatiq.brokers.redis import RedisBroker

from sereleum.constants.db import REDIS_PASSWORD, REDIS_PORT, REDIS_HOST


redis_client = redis.asyncio.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    db=2,
)

def get_broker():
   return RedisBroker(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
    )
