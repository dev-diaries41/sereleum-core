import numpy as np
import matplotlib.pyplot as plt

from typing import Optional
from io import BytesIO
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA

from smartscan import Assignments

from sereleum.items.item_manager import ItemManager
from sereleum.clusters.cluster_manager import ClusterManager



def get_cluster_plot(cluster_manager: ClusterManager, items_manager: ItemManager, n: int = 6) -> Optional[bytes]:
    top_clusters = cluster_manager.get_top_clusters(n)
    ids, metadatas, embeddings = items_manager.get_samples(1e5, cluster_ids=list(top_clusters.keys()))
    if not ids:
        return None
    existing_assignments = {item_id : metadata.cluster_id for item_id, metadata in zip(ids, metadatas)}
    return plot_clusters_bytes(ids, embeddings, existing_assignments)


def plot_clusters(ids: list[str], embeddings: list[np.ndarray], assignments: Assignments, method='tsne', random_state=42, output_path: Optional[str] = None):
    """
    Plots clusters from ClusterResult using 2D embeddings.

    Args:
        ids (list[str]): list of item IDs in the same order as embeddings.
        embeddings (list[np.ndarray]): list of embeddings (any dimension).
        cluster_result (ClusterResult): Result from IncrementalClusterer.
        method (str): Dimensionality reduction method: 'tsne' or 'pca'.
        random_state (int): Random seed for reproducibility.
    """
    embeddings_array = np.stack(embeddings, axis=0)
    
    if method == 'tsne':
        from sklearn.manifold import TSNE
        reduced = TSNE(n_components=2, random_state=random_state).fit_transform(embeddings_array)
    elif method == 'pca':
        from sklearn.decomposition import PCA
        reduced = PCA(n_components=2, random_state=random_state).fit_transform(embeddings_array)
    else:
        raise ValueError("method must be 'tsne' or 'pca'")

    # Get cluster IDs for each item
    cluster_ids = [assignments.get(i, "unassigned") for i in ids]

    # Assign a color to each cluster
    unique_clusters = list(set(cluster_ids))
    colors = plt.cm.tab20(np.linspace(0, 1, len(unique_clusters)))
    color_map = {cid: c for cid, c in zip(unique_clusters, colors)}

    # Plot each point
    plt.figure(figsize=(8, 6))
    for cid in unique_clusters:
        idxs = [i for i, c in enumerate(cluster_ids) if c == cid]
        plt.scatter(reduced[idxs, 0], reduced[idxs, 1], color=color_map[cid], label=cid, s=50, edgecolor='k')

    plt.title("Prompt Clusters")
    plt.xlabel("Dimension 1")
    plt.ylabel("Dimension 2")
    plt.legend(markerscale=2, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()
    
    if output_path:
        plt.savefig(output_path)


def plot_clusters_bytes(ids: list[str], embeddings: list[np.ndarray], assignments: Assignments, method='tsne', random_state=42) -> bytes:
    embeddings_array = np.stack(embeddings, axis=0)
    
    if method == 'tsne':
        reduced = TSNE(n_components=2, random_state=random_state).fit_transform(embeddings_array)
    elif method == 'pca':
        reduced = PCA(n_components=2, random_state=random_state).fit_transform(embeddings_array)
    else:
        raise ValueError("method must be 'tsne' or 'pca'")

    cluster_ids = [assignments.get(i, "unassigned") for i in ids]
    unique_clusters = list(set(cluster_ids))
    colors = plt.cm.tab20(np.linspace(0, 1, len(unique_clusters)))
    color_map = {cid: c for cid, c in zip(unique_clusters, colors)}

    fig, ax = plt.subplots(figsize=(8, 6))
    for cid in unique_clusters:
        idxs = [i for i, c in enumerate(cluster_ids) if c == cid]
        ax.scatter(reduced[idxs, 0], reduced[idxs, 1], color=color_map[cid], label=cid, s=50, edgecolor='k')

    ax.set_title("Prompt Clusters")
    ax.set_xlabel("Dimension 1")
    ax.set_ylabel("Dimension 2")
    ax.legend(markerscale=2, bbox_to_anchor=(1.05, 1), loc='upper left')
    fig.tight_layout()

    # Save to in-memory bytes buffer
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def plot_clusters_with_prototypes(
    ids: list[str],
    embeddings: list[np.ndarray],
    assignments: dict,
    prototype_ids: list[str],
    prototype_embeddings: list[np.ndarray],
    method='tsne',
    random_state=42,
    output_path: Optional[str] = None
):
    """
    Plots clusters with prototypes in 2D.

    Args:
        ids (list[str]): list of item IDs.
        embeddings (list[np.ndarray]): Embeddings corresponding to IDs.
        assignments (dict): Mapping from ID to cluster ID.
        prototype_ids (list[str]): list of prototype IDs.
        prototype_embeddings (list[np.ndarray]): Prototype embeddings.
        method (str): 'tsne' or 'pca'.
    """

    all_embeddings = np.concatenate([np.stack(embeddings), prototype_embeddings], axis=0)

    if method == 'tsne':
        reduced = TSNE(n_components=2, random_state=random_state).fit_transform(all_embeddings)
    elif method == 'pca':
        reduced = PCA(n_components=2, random_state=random_state).fit_transform(all_embeddings)
    else:
        raise ValueError("method must be 'tsne' or 'pca'")

    # Split reduced embeddings back
    reduced_points = reduced[:len(embeddings)]
    reduced_prototypes = reduced[len(embeddings):]

    # Cluster IDs for items
    cluster_ids = [assignments.get(i, "unassigned") for i in ids]

    # Unique clusters and colors
    unique_clusters = list(set(cluster_ids))
    colors = plt.cm.tab20(np.linspace(0, 1, len(unique_clusters)))
    color_map = {cid: c for cid, c in zip(unique_clusters, colors)}

    plt.figure(figsize=(8, 6))

    # Plot points
    for cid in unique_clusters:
        idxs = [i for i, c in enumerate(cluster_ids) if c == cid]
        plt.scatter(reduced_points[idxs, 0], reduced_points[idxs, 1], 
                    color=color_map[cid], label=cid, s=50, edgecolor='k', alpha=0.6)

    # Plot prototypes
    for i, pid in enumerate(prototype_ids):
        cid = assignments.get(pid, "unassigned")
        plt.scatter(reduced_prototypes[i, 0], reduced_prototypes[i, 1], 
                    color=color_map.get(cid, 'black'), marker='X', s=200, edgecolor='k', linewidth=1.5)

    plt.title("Clusters with Prototypes")
    plt.xlabel("Dimension 1")
    plt.ylabel("Dimension 2")
    plt.legend(markerscale=2, bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path)
    plt.show()