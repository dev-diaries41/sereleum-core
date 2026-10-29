from sereleum.index.redis_index_listener import RedisIndexListener
from domains.articles.item import Article

class ArticleIndexerListener(RedisIndexListener[Article]):
    pass