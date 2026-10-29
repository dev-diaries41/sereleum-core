
from sereleum.providers.types import TextEmbeddingModel

def get_embed_store_name(model: TextEmbeddingModel, item_name: str = 'item'):
    safe_model = model.replace("-", "_")
    return f"{item_name}_embeds_{safe_model}"
    