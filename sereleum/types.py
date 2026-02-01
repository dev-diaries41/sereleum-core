from typing import Literal
from sereleum.prompts.types import Prompt, PromptMetadata, PromptsOverviewInfo

# Long running jobs
FinishedStatus = Literal['complete', 'failed']
Status = Literal[
    FinishedStatus,
    "active",
    "delayed",
    "queued",
]

EmbeddingStoreType = Literal['cluster', 'prompt']
