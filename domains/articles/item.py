from datetime import datetime, timezone
from pydantic import Field

from sereleum.schemas.item import Item, ItemsOverviewInfo

class Article(Item):
    content: str
    title: str
    url: str
    published: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
 
class ArticlesOverviewInfo(ItemsOverviewInfo):
    pass
