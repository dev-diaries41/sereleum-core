# celery_tasks.py
from dotenv import load_dotenv
from revelium.prompts.types import Prompt
from revelium.main import indexer
import os
import json

load_dotenv()

REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")

import dramatiq
from dramatiq.middleware import AsyncIO
from dramatiq.brokers.redis import RedisBroker
from revelium.main import indexer
from revelium.prompts.types import Prompt
import json


redis_broker = RedisBroker(
    host=REDIS_HOST,
    port=6379,
    password=REDIS_PASSWORD,
)
redis_broker.add_middleware(AsyncIO())  # <--- critical for async tasks
dramatiq.set_broker(redis_broker)

@dramatiq.actor
async def index_prompts(file_path: str):
    with open(file_path) as f:
        prompts = [Prompt(**p) for p in json.load(f)]
    return await indexer.run(prompts)
