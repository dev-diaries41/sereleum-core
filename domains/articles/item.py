from datetime import datetime, timezone
from pydantic import Field

from sereleum.schemas.item import DocItem, ItemsOverviewInfo

class Article(DocItem):
    title: str
    url: str
    published: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
 
class ArticlesOverviewInfo(ItemsOverviewInfo):
    pass
