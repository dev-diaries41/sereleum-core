from sereleum.data.models import PromptModel, PromptClusterCrossRefModel, PromptClusterModel
from sereleum.schemas.items.prompt import Prompt
from sereleum.schemas.cluster import ClusterCrossRef, StoredClusterMetadata


def prompt_to_orm(prompt: Prompt) -> PromptModel:
    return PromptModel(
        id=prompt.id,
        content=prompt.content,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        tokens=prompt.tokens,
    )


def prompt_from_orm(prompt: PromptModel) -> Prompt:
    return Prompt(
        id=prompt.id,
        content=prompt.content,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        tokens=prompt.tokens,
    )


def cluster_to_orm(cluster: StoredClusterMetadata) -> PromptClusterModel:
    return PromptClusterModel(
        id=cluster.id,
        prototype_size=cluster.prototype_size,
        label=cluster.label,
        mean_similarity=cluster.mean_similarity,
        std_similarity=cluster.std_similarity,
    )


def cluster_from_orm(cluster: PromptClusterModel) -> StoredClusterMetadata:
    return StoredClusterMetadata(
        id=cluster.id,
        prototype_size=cluster.prototype_size,
        label=cluster.label,
        mean_similarity=cluster.mean_similarity,
        std_similarity=cluster.std_similarity,
    )



def crossref_to_prompt_orm(ref: ClusterCrossRef) -> PromptClusterCrossRefModel:
    return PromptClusterCrossRefModel(
        item_id=ref.item_id,
        cluster_id=ref.cluster_id,
    )


def crossref_from_prompt_orm(ref: PromptClusterCrossRefModel) -> ClusterCrossRef:
    return ClusterCrossRef(
        item_id=ref.item_id,
        cluster_id=ref.cluster_id,
    )