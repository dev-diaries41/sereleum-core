import tiktoken
from openai.types import ResponsesModel


def count_tokens_embedding(text: str, model: ResponsesModel) -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


def embedding_token_cost(text: str, price_per_1m_tokens: float, model: ResponsesModel) -> float:
    tokens = count_tokens_embedding(text, model)
    return tokens * (price_per_1m_tokens / 1_000_000)
    

