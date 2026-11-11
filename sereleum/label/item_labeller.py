import asyncio
from typing import List

from llm_connect.providers.llm_provider import LLMProvider
from sereleum.schemas.llm import (
    LLMClassificationResult,
    BatchLLMClassificationResult,
)
from sereleum.schemas.item import DocItem

# TODO: create BatchProcessor implementation

class ItemLabeller:
    def __init__(
        self,
        llm: LLMProvider,
        label_confidence_threshold: float = 0.8,
        label_concurrency: int = 8,
        batch_size: int = 8
    ):
        if label_concurrency < 1:
            raise ValueError("label_concurrency must be at least 1")
        
        self.batch_size = batch_size
        self.llm = llm
        self.label_confidence_threshold = label_confidence_threshold
        self.label_concurrency = label_concurrency

    async def label_items(self, items: list[DocItem]) -> dict[str, str]:
        if not items:
            return {}

        batches = self._chunk_items(items)
        semaphore = asyncio.Semaphore(self.label_concurrency)

        tasks = [
            self._label_batch_with_sem(semaphore, batch)
            for batch in batches
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        labelled_items: dict[str, str] = {}

        for batch, result in zip(batches, results):
            if isinstance(result, BaseException):
                print(f"[WARNING] Error labelling batch | Details: {result}")
                continue

            if len(result) != len(batch):
                print(
                    f"[WARNING] Batch result count mismatch | "
                    f"Expected: {len(batch)}, Received: {len(result)}"
                )
                continue

            for item, classification in zip(batch, result):
                if not classification.label:
                    continue

                if classification.confidence < self.label_confidence_threshold:
                    print(
                        f"[WARNING] Item {item.id} not labelled | "
                        f"Details: Below confidence threshold: "
                        f"confidence={classification.confidence}"
                    )
                    continue

                labelled_items[item.id] = classification.label

        return labelled_items

    async def _label_batch_with_sem( self, semaphore: asyncio.Semaphore, items: list[DocItem], ) -> list[LLMClassificationResult]:
        async with semaphore:
            return await asyncio.to_thread(self.label_batch, items)


    def _label_batch(self, items: list[DocItem]) -> List[LLMClassificationResult]:
        if not items:
            return []

        input_prompt = self._get_labelling_prompt(items)
        response = self.llm.generate_json( input_prompt, BatchLLMClassificationResult)
        return response.results

    def _chunk_items(self, items: list[DocItem]) -> list[list[DocItem]]:
        return [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]

    @staticmethod
    def _get_labelling_prompt(items: list[DocItem]) -> str:
        return "\n\n".join(
            f"""
            ## ItemId: {item.id}

            Content:

            {item.content}
            """
            for item in items
        )