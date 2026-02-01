import numpy as np
import matplotlib.pyplot as plt

from typing import Optional, List
from io import BytesIO
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from smartscan import Assignments
from sereleum.clusters.incremental_cluster import IncrementalClusterer
from sereleum.prompts.prompts_manager import PromptsManager
from sereleum.clusters.clusters_manager import ClustersManager


## TODO: return n_label
async def cluster_prompts(prompts_manager: PromptsManager, cluster_manager: ClustersManager, auto_label: bool = True, auto_merge_threshold: float = 0.9, initial_threshold: float = 0.3):
    ids, metadatas, embeddings = prompts_manager.get_prompt_metadata_samples(1e5)
    existing_clusters = cluster_manager.get_all_clusters()
    existing_assignments = {prompt_id : metadata.cluster_id for prompt_id, metadata in zip(ids, metadatas)}
    clusterer = IncrementalClusterer(
        default_threshold=initial_threshold,
        merge_threshold=auto_merge_threshold,
        existing_assignments=existing_assignments,
        existing_clusters=existing_clusters,
    )
    result = clusterer.cluster(ids, embeddings)
    if result.assignments:
        prompts_manager.update_prompts_from_assignments(result.assignments, result.merges)
    if result.clusters:
        unlabelled = await cluster_manager.update_clusters(result.clusters, result.merges)
        if len(unlabelled) > 0 and auto_label:
            n_labelled = await cluster_manager.label_and_update_clusters(unlabelled)
    return result

def get_cluster_plot(prompts_manager: PromptsManager) -> Optional[bytes]:
    ids, metadatas, embeddings = prompts_manager.get_prompt_metadata_samples(1e5)
    if not ids:
        return None
    existing_assignments = {prompt_id : metadata.cluster_id for prompt_id, metadata in zip(ids, metadatas)}
    return plot_clusters_bytes(ids, embeddings, existing_assignments)


def plot_clusters(ids: List[str], embeddings: List[np.ndarray], assignments: Assignments, method='tsne', random_state=42, output_path: Optional[str] = None):
    """
    Plots clusters from ClusterResult using 2D embeddings.

    Args:
        ids (List[str]): List of item IDs in the same order as embeddings.
        embeddings (List[np.ndarray]): List of embeddings (any dimension).
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


def plot_clusters_bytes(ids: List[str], embeddings: List[np.ndarray], assignments: Assignments, method='tsne', random_state=42) -> bytes:
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
    ids: List[str],
    embeddings: List[np.ndarray],
    assignments: dict,
    prototype_ids: List[str],
    prototype_embeddings: List[np.ndarray],
    method='tsne',
    random_state=42,
    output_path: Optional[str] = None
):
    """
    Plots clusters with prototypes in 2D.

    Args:
        ids (List[str]): List of item IDs.
        embeddings (List[np.ndarray]): Embeddings corresponding to IDs.
        assignments (dict): Mapping from ID to cluster ID.
        prototype_ids (List[str]): List of prototype IDs.
        prototype_embeddings (List[np.ndarray]): Prototype embeddings.
        method (str): 'tsne' or 'pca'.
    """
    import matplotlib.pyplot as plt
    import numpy as np
    from sklearn.manifold import TSNE
    from sklearn.decomposition import PCA

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
