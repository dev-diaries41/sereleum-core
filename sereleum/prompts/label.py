
import asyncio

from sereleum.schemas.llm import LLMClassificationResult
from sereleum.providers.llm.llm_client import LLMClient
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.prompts.prompts import get_labelling_prompt

def label_prompts(llm: LLMClient, prompts_manager: PromptsManager, cluster_id: str, sample_size: int, existing_labels: list[str]) -> LLMClassificationResult:
    prompts = prompts_manager.embedding_store.get(filter={"cluster_id": cluster_id},  limit=sample_size, include=['documents'])
    sample_prompts = [content for content in prompts.datas]
    input_prompt = get_labelling_prompt(cluster_id, existing_labels, sample_prompts)
    return llm.generate_json(input_prompt, LLMClassificationResult)

async def async_label_prompts(semaphore:  asyncio.Semaphore, llm: LLMClient, prompts_manager: PromptsManager, cluster_id: str, sample_size: int, existing_labels: list[str]):
    async with semaphore:
        return await asyncio.to_thread(label_prompts, llm, prompts_manager, cluster_id, sample_size, existing_labels)

