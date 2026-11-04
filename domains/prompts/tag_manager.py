from sereleum.tags.tag_manager import TagManager

from domains.prompts.stores import  PromptTagCrossRefStore, PromptTagStore

from sqlalchemy.ext.asyncio import async_sessionmaker


def create_tag_manager(sessionmaker: async_sessionmaker):
    tag_store = PromptTagStore(sessionmaker)
    tag_crossref_store = PromptTagCrossRefStore(sessionmaker)
    return TagManager(
        tag_store=tag_store,
        crossrefs_store=tag_crossref_store,
    )