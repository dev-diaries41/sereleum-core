from numpy import ndarray
from typing import List, Generator, Any

from smartscan import GetResult, QueryResult
from smartscan.embeds import EmbeddingStore

from sereleum.store.items_manager import ItemsManager
from sereleum.prompts.types import Prompt, PromptMetadata

class PromptsManager(ItemsManager[Prompt, str, PromptMetadata]):
    def __init__(self, embedding_store: EmbeddingStore,): 
        super().__init__(embedding_store)     


    def to_items(self, result: GetResult | QueryResult) -> List[Prompt]:
        return [ Prompt(prompt_id=prompt_id, content=prompt_content,  metadata=PromptMetadata(**metadata)) for prompt_id, metadata, prompt_content in zip(result.ids, result.metadatas, result.datas) ]
    
    def to_item_tuples(self, result: GetResult | QueryResult, with_embeddings: bool = False)  -> Generator[tuple[str, PromptMetadata] | tuple[str, PromptMetadata, ndarray], Any, None]:
        if not with_embeddings:
            return [ (prompt_id, PromptMetadata(**metadata)) for prompt_id, metadata in zip(result.ids, result.metadatas)]
        if len(result.embeddings) > 0 and with_embeddings:
            return [(prompt_id, PromptMetadata(**metadata), emb) for prompt_id, metadata, emb in zip(result.ids, result.metadatas, result.embeddings)]        
        else:
            raise ValueError("With embeddings is true but result has no embeddings")
        