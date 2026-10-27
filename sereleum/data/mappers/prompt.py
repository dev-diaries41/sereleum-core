
from sereleum.data.models import PromptModel, PromptClusterCrossRefModel, PromptClusterModel
from sereleum.schemas.items.prompt import Prompt
from sereleum.schemas.cluster import ClusterCrossRef, StoredClusterMetadata
from sereleum.data.mappers.mapper import Mapper


class PromptMapper(Mapper[PromptModel, Prompt]):
    def to_domain(self, entity: PromptModel) -> Prompt:
        return Prompt(
            id=entity.id,
            content=entity.content,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            tokens=entity.tokens,
        )

    def to_entity(self, domain: Prompt) -> PromptModel:
        return PromptModel(
            id=domain.id,
            content=domain.content,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
            tokens=domain.tokens,
        )


class PromptClusterMapper(Mapper[PromptClusterModel, StoredClusterMetadata]):
    def to_domain(self, entity: PromptClusterModel) -> StoredClusterMetadata:
        return StoredClusterMetadata(
            id=entity.id,
            prototype_size=entity.prototype_size,
            label=entity.label,
            mean_similarity=entity.mean_similarity,
            std_similarity=entity.std_similarity,
        )

    def to_entity(self, domain: StoredClusterMetadata) -> PromptClusterModel:
        return PromptClusterModel(
            id=domain.id,
            prototype_size=domain.prototype_size,
            label=domain.label,
            mean_similarity=domain.mean_similarity,
            std_similarity=domain.std_similarity,
        )


class PromptClusterCrossRefMapper(Mapper[PromptClusterCrossRefModel, ClusterCrossRef]):
    def to_domain(self, entity: PromptClusterCrossRefModel) -> ClusterCrossRef:
        return ClusterCrossRef(
            item_id=entity.item_id,
            cluster_id=entity.cluster_id,
        )

    def to_entity(self, domain: ClusterCrossRef) -> PromptClusterCrossRefModel:
        return PromptClusterCrossRefModel(
            item_id=domain.item_id,
            cluster_id=domain.cluster_id,
        )
