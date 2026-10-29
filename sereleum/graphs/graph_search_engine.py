import heapq
import networkx as nx
import numpy as np

from dataclasses import dataclass, field
from smartscan.embeds.embedding_store import EmbeddingStore


@dataclass(order=True)
class GraphPath:
    priority: float
    hops: int
    node_id: str = field(compare=False)
    path: list[str] = field(compare=False)


class GraphSearchEngine:
    def __init__(
        self,
        embed_store: EmbeddingStore,
        graph: nx.Graph,
        neighbors_per_node: int = 2,
        min_seed_similarity: float = 0.5,
        min_edge_similarity: float = 0.7,
        max_edge_similarity: float = 0.95,
        threshold_growth: float = 0.05,
        drift_penalty: float = 0.15,
    ):
        self.embed_store = embed_store
        self.graph = graph
        self.neighbors_per_node = neighbors_per_node
        self.min_seed_similarity = min_seed_similarity
        self.min_edge_similarity = min_edge_similarity
        self.max_edge_similarity = max_edge_similarity
        self.threshold_growth = threshold_growth
        self.drift_penalty = drift_penalty

    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int | None = None,
    ) -> list[str]:
        query_embedding = np.asarray(query_embedding)
        if np.linalg.norm(query_embedding) == 0:
            return []

        result = await self.embed_store.query(
            query_embedding,
            topK=1,
            include_sims=True,
        )
        if len(result.ids) == 0 or not result.sims:
            return []

        seed = result.ids[0]
        seed_similarity = result.sims[0]

        if seed_similarity < self.min_seed_similarity:
            return []
        if seed not in self.graph:
            return []

        best_score = {seed: seed_similarity}
        queue = [GraphPath(-seed_similarity, 0, seed, [seed])]

        while queue:
            state = heapq.heappop(queue)
            score = -state.priority
            node = state.node_id

            if score < best_score.get(node, -float("inf")):
                continue

            threshold = min( self.max_edge_similarity, self.min_edge_similarity + self.threshold_growth * state.hops)

            neighbors = sorted(
                (
                    (neighbor, float(data["weight"]))
                    for neighbor, data in self.graph[node].items()
                    # Prevent cycles within the current path.
                    # A node may still be reached through a different path.
                    if neighbor not in state.path
                    and data["weight"] >= threshold
                ),
                key=lambda item: item[1],
                reverse=True,
            )[:self.neighbors_per_node]

            for neighbor, edge_weight in neighbors:
                hops = state.hops + 1
                new_score = ( score * edge_weight * np.exp(-self.drift_penalty * hops) )

                if new_score > best_score.get(neighbor, -float("inf")):
                    best_score[neighbor] = new_score
                    heapq.heappush(
                        queue,
                        GraphPath( -new_score, hops, neighbor, state.path + [neighbor], ),
                    )

        node_ids = [
            node_id
            for node_id, _ in sorted(
                best_score.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

        return node_ids if top_k is None else node_ids[:top_k]