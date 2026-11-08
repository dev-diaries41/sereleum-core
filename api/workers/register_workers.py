import json
import os
from time import perf_counter

import dramatiq
from dramatiq.middleware import AsyncIO, CurrentMessage

from api.redis import redis_client, get_broker
from api.schemas.response import FailMessage, CompleteMessage, ActiveMessage
from sereleum.helpers import get_cluster_status_key, get_cluster_status_channel
from sereleum.logs import getLogger

from sereleum.index.types import Indexer
from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.data.types import TItem

from sereleum.index.redis_index_listener import RedisIndexListener

def register_workers(item_cls: type[TItem], indexer: Indexer[TItem], cluster_manager: ClusterManager[TItem]):
    redis_broker = get_broker()
    redis_broker.add_middleware(AsyncIO())
    redis_broker.add_middleware(CurrentMessage())
    dramatiq.set_broker(redis_broker)

    logger = getLogger("tasks", "logs/tasks.log")

    @dramatiq.actor(max_retries=2)
    async def index_worker(
        file_path: str,
        auto_label: bool = True,
        default_threshold: float = 0.55,
    ):
        msg = CurrentMessage().get_current_message()
        job_id = msg.message_id

        try:
            with open(file_path) as f:
                items = [item_cls(**p) for p in json.load(f)]
            
            indexer.register_listener(RedisIndexListener[TItem](msg.message_id, redis_client))
            await indexer.run(items)

            cluster_worker.send(
                index_job_id=job_id,
                auto_label=auto_label,
                default_threshold=default_threshold,
            )
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)


    @dramatiq.actor(max_retries=2)
    async def cluster_worker(
        index_job_id: str,
        auto_label: bool = True,
        default_threshold: float = 0.3,
    ):
        msg = CurrentMessage().get_current_message()
        retries = msg.options.setdefault("retries", 0)

        status_key = get_cluster_status_key(index_job_id)
        channel = get_cluster_status_channel(index_job_id)

        if retries + 1 > 2:
            await redis_client.set(status_key, "failed", ex=86400)
            await redis_client.publish(
                channel,
                FailMessage(error="cluster job failed").model_dump_json(),
            )
            logger.error(f"cluster job failed: {index_job_id}")
            return

        await redis_client.set(status_key, "active", ex=86400)
        await redis_client.publish(channel, ActiveMessage().model_dump_json())

        start = perf_counter()

        result = await cluster_manager.cluster(
            auto_label=auto_label,
            default_threshold=default_threshold,
        )

        elapsed = perf_counter() - start

        await redis_client.set(status_key, "complete", ex=86400)
        await redis_client.publish(
            channel,
            CompleteMessage(
                total_processed=len(result.assignments),
                time_elapsed=elapsed,
            ).model_dump_json(),
        )

    return index_worker, cluster_worker