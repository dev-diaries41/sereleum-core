import networkx as nx
import numpy as np

from itertools import combinations
from pathlib import Path

from sereleum.graphs.node import Node


def build_graph(
    nodes: list[Node],
    embeddings: dict[str, np.ndarray],
    threshold: float = 0.7,
) -> nx.Graph:
    graph = nx.Graph()

    for node in nodes:
        graph.add_node(node.id, label=node.label)

    for a, b in combinations(nodes, 2):
        if a.id not in embeddings or b.id not in embeddings:
            continue

        emb_a = embeddings[a.id]
        emb_b = embeddings[b.id]
        denom = np.linalg.norm(emb_a) * np.linalg.norm(emb_b)

        similarity = (
            float(np.dot(emb_a, emb_b) / denom)
            if denom
            else 0.0
        )

        if similarity >= threshold:
            graph.add_edge(a.id, b.id, weight=similarity)

    return graph


def save_graph(graph: nx.Graph, path: str | Path) -> None:
    nx.write_graphml(graph, path)


def load_graph(path: str | Path) -> nx.Graph:
    return nx.read_graphml(path)