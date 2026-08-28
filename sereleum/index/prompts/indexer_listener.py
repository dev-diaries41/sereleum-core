from redis.asyncio import Redis

from smartscan import StoredEmbedding
from smartscan.processor import ProcessorListener

from sereleum.types import Status
from sereleum.schemas.items.prompt import Prompt
from sereleum.helpers import get_index_progres_key, get_index_status_key, get_index_progress_channel
from sereleum.schemas.api import ProgressMessage, FailMessage, CompleteMessage, ErrorMessage


class PromptIndexListener(ProcessorListener[Prompt, tuple[StoredEmbedding, Prompt]]):
    def __init__(self, job_id: str, redis_client: Redis):
        self.job_id = job_id
        self.redis = redis_client

    async def on_active(self):
        await self._update_status('active')

    async def on_complete(self, result):
        await self._update_status('complete')
        await self.redis.publish(
            get_index_progress_channel(self.job_id), 
            CompleteMessage(total_processed=result.total_processed, time_elapsed=result.time_elapsed).model_dump_json()
            )


    async def on_progress(self, progress):
        await self.redis.set(get_index_progres_key(self.job_id), progress, ex=86400)
        await self.redis.publish(get_index_progress_channel(self.job_id), ProgressMessage(progress=progress).model_dump_json())

    async def on_fail(self, result):
        print(f"Indexing failed: {result.error}")
        await self._update_status('failed')
        await self.redis.publish(get_index_progress_channel(self.job_id), FailMessage(error=str(result.error)).model_dump_json())

    async def on_error(self, e, item):
        print(f"Error processing prompt: {item.id}. Details: {e}")
        await self.redis.publish(get_index_progress_channel(self.job_id), ErrorMessage(error=str(e), item=item.id).model_dump_json())

    async def _update_status(self, status: Status ):
        await self.redis.set(get_index_status_key(self.job_id), status, ex=86400)
