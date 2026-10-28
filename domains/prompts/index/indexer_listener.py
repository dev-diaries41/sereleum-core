from sereleum.index.redis_index_listener import RedisIndexListener
from domains.prompts.prompt import Prompt

class PromptIndexerListener(RedisIndexListener[Prompt]):
    pass