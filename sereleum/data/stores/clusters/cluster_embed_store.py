
from sereleum.data.stores.clusters.cluster_store import ClusterStore

from smartscan.embeds.embedding_store import EmbeddingStore


class ClusterEmbedStore:
    def __init__(self, clusters: ClusterStore, embeds: EmbeddingStore):
        self.clusters = clusters
        self.embeds = embeds