from tqdm import tqdm
from redis import Redis

from smartscan import ItemEmbedding
from smartscan.processor import ProcessorListener

from revelium.types import Prompt, Status
from revelium.cluster import cluster_prompts
from revelium.prompts_manager import PromptsManager

class DefaultIndexerListener(ProcessorListener[Prompt, ItemEmbedding]):
    def on_error(self, e, item):
        print(e)
    def on_fail(self, result):
        return print(result.error)


class ProgressBarIndexerListener(ProcessorListener[Prompt, ItemEmbedding]):
    def __init__(self):
        self.progress_bar = tqdm(total=100, desc="Indexing")

    async def on_progress(self, progress):
        self.progress_bar.n = int(progress * 100)
        self.progress_bar.refresh()
        
    async def on_fail(self, result):
        self.progress_bar.close()
        print(result.error)

    async def on_error(self, e, item):
        print(e)
    
    async def on_complete(self, result):
        self.progress_bar.close()
        print(f"Results: {result.total_processed} | Time elapsed: {result.time_elapsed:.4f}s")


class PromptIndexListenerWithProgressBar(ProgressBarIndexerListener):
    def __init__(self, prompts_manager: PromptsManager):
        super().__init__()
        self.prompts_manager = prompts_manager

    async def on_complete(self, result):
        await super().on_complete(result)
        cluster_prompts(self.prompts_manager)


class PromptIndexListener(ProcessorListener[Prompt, ItemEmbedding]):
    def __init__(self, job_id: str, redis_client: Redis):
        self.job_id = job_id
        self.redis = redis_client

    async def on_active(self):
        self._update_status('active')

    async def on_complete(self, result):
        self._update_status('complete')
        # print(f"Job complete - status: {self.redis.get(self._get_status_key())} | progress: {self.redis.get(self._get_progres_key())}")

    async def on_progress(self, progress):
        self.redis.set(self._get_progres_key(), progress, ex=86400)

    async def on_fail(self, result):
        print(f"Indexing failed: {result.error}")
        self._update_status('failed')

    async def on_error(self, e, item):
        print(f"Error processing prompt: {item.prompt_id}. Details: {e}")

    def _get_progres_key(self):
        return f"progress_{self.job_id}"
    
    def _get_status_key(self):
        return f"status_{self.job_id}"
    
    def _update_status(self, status: Status ):
        self.redis.set(self._get_status_key(), status, ex=86400)