from sereleum.schemas.items.prompt import Prompt
from sereleum.index.redis_index_listener import RedisIndexListener

class PromptIndexer(RedisIndexListener[Prompt]):
    pass