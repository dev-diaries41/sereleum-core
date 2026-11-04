from sereleum.tags.tag_manager import TagManager

from domains.articles.stores import  ArticleTagStore, ArticleTagCrossRefStore

from sqlalchemy.ext.asyncio import async_sessionmaker


def create_tag_manager(sessionmaker: async_sessionmaker):
    tag_store = ArticleTagStore(sessionmaker)
    tag_crossref_store = ArticleTagCrossRefStore(sessionmaker)
    return TagManager(
        tag_store=tag_store,
        crossrefs_store=tag_crossref_store,
    )