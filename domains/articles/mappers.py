
from domains.articles.models import ArticleClusterModel, ArticleClusterCrossRefModel, ArticleModel
from domains.articles.item import Article
from sereleum.schemas.cluster import ClusterCrossRef, StoredClusterMetadata
from sereleum.data.mappers.mapper import Mapper


class ArticleMapper(Mapper[ArticleModel, Article]):
    def to_domain(self, entity: ArticleModel) -> Article:
        return Article(
            title=entity.title,
            url=entity.url,
            id=entity.id,
            content=entity.content,
            published=entity.published,
        )

    def to_entity(self, domain: Article) -> ArticleModel:
        return ArticleModel(
            id=domain.id,
            url=domain.url,
            title=domain.title,
            content=domain.content,
            published=domain.published,
        )


class ArticleClusterMapper(Mapper[ArticleClusterModel, StoredClusterMetadata]):
    def to_domain(self, entity: ArticleClusterModel) -> StoredClusterMetadata:
        return StoredClusterMetadata(
            id=entity.id,
            prototype_size=entity.prototype_size,
            label=entity.label,
            mean_similarity=entity.mean_similarity,
            std_similarity=entity.std_similarity,
        )

    def to_entity(self, domain: StoredClusterMetadata) -> ArticleClusterModel:
        return ArticleClusterModel(
            id=domain.id,
            prototype_size=domain.prototype_size,
            label=domain.label,
            mean_similarity=domain.mean_similarity,
            std_similarity=domain.std_similarity,
        )


class ArticleClusterCrossRefMapper(Mapper[ArticleClusterCrossRefModel, ClusterCrossRef]):
    def to_domain(self, entity: ArticleClusterCrossRefModel) -> ClusterCrossRef:
        return ClusterCrossRef(
            item_id=entity.item_id,
            cluster_id=entity.cluster_id,
        )

    def to_entity(self, domain: ClusterCrossRef) -> ArticleClusterCrossRefModel:
        return ArticleClusterCrossRefModel(
            item_id=domain.item_id,
            cluster_id=domain.cluster_id,
        )
