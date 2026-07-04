from sereleum.data.clusters.cluster_crossref_entity import make_cluster_crossref_entity
from sereleum.data.prompts.prompt_cluster_entitiy import PromptClusterEntity
from sereleum.data.prompts.prompt_entitiy import PromptEntity
from sereleum.data.table_names import TableNames

PromptClusterCrossRefEntity = make_cluster_crossref_entity(
    table=TableNames.PROMPT_CLUSTER_CROSSREFS.value,
    cluster_entity=PromptClusterEntity,
    item_entity=PromptEntity
)