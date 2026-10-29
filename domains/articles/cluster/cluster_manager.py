from sereleum.clusters.cluster_manager import ClusterManager
from sereleum.schemas.llm import LLMClassificationResult
from sereleum.schemas.cluster import ClusterCrossRefFilter
from sereleum.data.embeds.pgvector_embed_store import PgVectorEmbeddingStore

from domains.articles.item import ArticleFilter, Article
from domains.articles.stores import ArticleStore, ArticleClusterStore, ArticleClusterCrossRefStore

from sqlalchemy.ext.asyncio import async_sessionmaker
from llm_connect.providers.llm_provider import LLMProvider


class ArticleClusterManager(ClusterManager[Article]):    
    async def label(self, cluster_id, sample_size) -> LLMClassificationResult:
        result = await self.cluster_embedding_store.get([cluster_id])
        if len(result) == 0:
            raise ValueError("Cluster not found")
        cluster_embed = result[0]
        
        ## Note: consider skipping this step and directly querying embed store without using the filter ids since items in the same cluster are most likely to be in topK
        crossrefs = await self.crossrefs_store.get(filter=ClusterCrossRefFilter(include_cluster_ids=[cluster_id]))
        ids = [c.item_id for c in crossrefs]
        query_result = await self.item_embedding_store.query(query_embed=cluster_embed.embedding, ids=ids, topK=sample_size)
        sample_contents = [item.content for item in await self.item_store.get(filter=ArticleFilter(ids=query_result.ids))]
        input_prompt = self._get_labelling_prompt(cluster_id, sample_contents)
        return self.llm.generate_json(input_prompt, LLMClassificationResult)
    
    
    @staticmethod
    def _get_labelling_prompt(cluster_id: str, sample_contents: list[str]) -> str:
        return f"""## ClusterId: {cluster_id}\n\n Cluster sample items \n\n {sample_contents}"""


def get_cluster_manager(sessionmaker: async_sessionmaker, embed_dim:int, llm: LLMProvider):
    item_store = ArticleStore(sessionmaker)
    cluster_store = ArticleClusterStore(sessionmaker)
    cluster_crossref_store = ArticleClusterCrossRefStore(sessionmaker)
    item_embed_store = PgVectorEmbeddingStore(name='article_embeds', sessionmaker=sessionmaker, dim=embed_dim)
    cluster_embed_store = PgVectorEmbeddingStore(name='article_cluster_embeds', sessionmaker=sessionmaker, dim=embed_dim)
    return ArticleClusterManager(
        cluster_embedding_store=cluster_embed_store,
        cluster_store=cluster_store,
        crossrefs_store=cluster_crossref_store,
        item_embedding_store=item_embed_store, 
        item_store=item_store,
        llm=llm,
    )