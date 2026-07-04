from enum import Enum

class TableNames(str, Enum):
    PROMPTS = "prompts"
    PROMPT_CLUSTERS = "prompt_clusters"
    PROMPT_CLUSTER_CROSSREFS = "prompt_cluster_crossrefs"