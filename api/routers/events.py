import json

from fastapi import Request, APIRouter
from sse_starlette import EventSourceResponse

from api.redis import redis_client
from api.routers.routes import Routes
from api.schemas.response import FailMessage, CompleteMessage, ProgressMessage, ActiveMessage

from sereleum.helpers import get_index_progres_key, get_index_status_key, get_cluster_status_key, get_cluster_status_channel, get_index_progress_channel

def create_events_router() -> APIRouter:
    router = APIRouter()

    @router.get(Routes.INDEX_PROGRESS_EVENT_ENDPOINT)
    async def track_index_progress_route(request: Request, job_id: str):
        async def event_generator():
            pubsub = redis_client.pubsub()
            channel = get_index_progress_channel(job_id)

            progress = await redis_client.get(get_index_progres_key(job_id))
            status = await redis_client.get(get_index_status_key(job_id))

            if progress is not None:
                yield {"event": "progress", "data": ProgressMessage(progress=float(progress)).model_dump_json()}

            if status == "active":
                yield {"event": "active", "data": ActiveMessage().model_dump_json()}

            elif status == "failed":
                yield {"event": "failed", "data": FailMessage(error="error indexing items").model_dump_json()}
                return

            elif status == "complete":
                yield {"event": "complete", "data": CompleteMessage().model_dump_json()}
                return

            await pubsub.subscribe(channel)

            try:
                while True:
                    if await request.is_disconnected():
                        break

                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0
                    )
                    if not message:
                        continue

                    data = json.loads(message["data"])

                    yield {
                        "event": data["event"],
                        "data": json.dumps(data)
                    }

                    if data["event"] in ("complete", "failed"):
                        break

            finally:
                await pubsub.unsubscribe(channel)
                await pubsub.close()

        return EventSourceResponse(event_generator())

    @router.get(Routes.CLUSTER_STATUS_EVENT_ENDPOINT)
    async def track_cluster_status(request: Request, job_id: str):

        async def event_generator():
            pubsub = redis_client.pubsub()
            channel = get_cluster_status_channel(job_id)

            status_key = get_cluster_status_key(job_id)
            status = await redis_client.get(status_key)

            if status == "active":
                yield {"event": "active", "data": ActiveMessage().model_dump_json()}

            elif status == "failed":
                yield {
                    "event": "failed",
                    "data": FailMessage(error="error clustering items").model_dump_json()
                }
                return

            elif status == "complete":
                yield {"event": "complete", "data": CompleteMessage().model_dump_json()}
                return

            await pubsub.subscribe(channel)

            try:
                while True:
                    if await request.is_disconnected():
                        break

                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0
                    )
                    if not message:
                        continue

                    data = json.loads(message["data"])

                    yield {
                        "event": data["event"],
                        "data": message["data"]
                    }

                    if data["event"] in ("complete", "failed"):
                        break

            finally:
                await pubsub.unsubscribe(channel)
                await pubsub.close()

        return EventSourceResponse(event_generator())


    return router