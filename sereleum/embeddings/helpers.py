
from sereleum.providers.types import TextEmbeddingModel
from sereleum.embeddings.chroma_store import ChromaDBEmbeddingStore
from sereleum.types import EmbeddingStoreType
import chromadb

# helps ensure each collection get embeddings of the right size
def get_embedding_collection_name( type: str, model: TextEmbeddingModel, embed_dim: int) -> str:
    return f"{type}_{model}_{embed_dim}_collection"
    
def get_embedding_store(type:EmbeddingStoreType, model: TextEmbeddingModel, embedding_dim: int ):
    client = chromadb.HttpClient(host='chromadb', port=8000, settings=chromadb.Settings(anonymized_telemetry=False))
    return ChromaDBEmbeddingStore(client.get_or_create_collection(
                get_embedding_collection_name(type, model, embedding_dim))
            ) 