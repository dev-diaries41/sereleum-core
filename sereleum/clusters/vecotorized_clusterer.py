import numpy as np
import uuid
from typing import List, Dict, Optional
from smartscan import Cluster, ClusterMetadata

class IncrementalClustererVectorized:
    """
    Optimized vectorized incremental clusterer:
    - Avoids np.vstack / np.append per item by preallocating arrays and resizing by doubling.
    - Uses O(1) mapping cluster_id -> index with `cluster_id_to_idx`.
    - Keeps in-place updates to numpy arrays.
    - Maintains Cluster objects for compatibility.
    """

    def __init__(
        self,
        dim: int,
        default_threshold: float = 0.3,
        min_cluster_size: int = 2,
        top_k: int = 3,
        initial_capacity: int = 16,
    ):
        self.dim = dim
        self.default_threshold = default_threshold
        self.min_cluster_size = min_cluster_size
        self.top_k = top_k

        # Cluster storage (object view)
        self.clusters: Dict[str, Cluster] = {}
        self.assignments: Dict[str, str] = {}

        # Vectorized state (preallocated)
        self._capacity = max(1, initial_capacity)
        self._n = 0  # number of active clusters

        self.cluster_ids: List[str] = []  # index -> cluster_id
        self.cluster_id_to_idx: Dict[str, int] = {}  # cluster_id -> index

        self.cluster_embeddings = np.empty((self._capacity, dim), dtype=np.float64)
        self.prototype_sizes = np.empty(self._capacity, dtype=np.int64)
        self.mean_sims = np.empty(self._capacity, dtype=np.float64)
        self.std_sims = np.empty(self._capacity, dtype=np.float64)

    def _generate_id(self) -> str:
        return uuid.uuid4().hex

    def _ensure_capacity(self):
        if self._n < self._capacity:
            return
        new_cap = self._capacity * 2
        self.cluster_embeddings = np.vstack([self.cluster_embeddings, np.empty((new_cap - self._capacity, self.dim), dtype=self.cluster_embeddings.dtype)])
        self.prototype_sizes = np.concatenate([self.prototype_sizes, np.empty(new_cap - self._capacity, dtype=self.prototype_sizes.dtype)])
        self.mean_sims = np.concatenate([self.mean_sims, np.empty(new_cap - self._capacity, dtype=self.mean_sims.dtype)])
        self.std_sims = np.concatenate([self.std_sims, np.empty(new_cap - self._capacity, dtype=self.std_sims.dtype)])
        self._capacity = new_cap

    def _add_cluster(self, item_id: str, embedding: np.ndarray):
        pid = self._generate_id()

        # ensure capacity
        self._ensure_capacity()
        idx = self._n

        # normalize input embedding dtype/shape
        emb = np.asarray(embedding, dtype=np.float64)
        if emb.shape[0] != self.dim:
            raise ValueError(f"embedding dim {emb.shape[0]} != expected {self.dim}")

        # store cluster object
        meta = ClusterMetadata(
            prototype_size=1,
            mean_similarity=self.default_threshold,
            std_similarity=0.0,
            label=Cluster.UNLABELLED,
        )
        cluster = Cluster(prototype_id=pid, embedding=emb.copy(), metadata=meta, label=Cluster.UNLABELLED)
        self.clusters[pid] = cluster

        # vectorized arrays (in-place)
        self.cluster_embeddings[idx] = emb
        self.prototype_sizes[idx] = 1
        self.mean_sims[idx] = self.default_threshold
        self.std_sims[idx] = 0.0

        # index bookkeeping
        self.cluster_ids.append(pid)
        self.cluster_id_to_idx[pid] = idx
        self._n += 1

        # assignment
        self.assignments[item_id] = pid

    def _update_cluster(self, item_id: str, embedding: np.ndarray, cid: str):
        idx = self.cluster_id_to_idx[cid]
        cluster = self.clusters[cid]

        emb = np.asarray(embedding, dtype=np.float64)
        old_size = cluster.metadata.prototype_size
        old_mean = cluster.metadata.mean_similarity
        old_std = cluster.metadata.std_similarity

        # incremental update (in-place)
        new_size = old_size + 1
        new_embedding = (cluster.embedding * old_size + emb) / new_size
        sim_new = float(np.dot(new_embedding, emb))
        new_mean = (old_mean * old_size + sim_new) / new_size
        new_std = np.sqrt(((old_size - 1) * (old_std ** 2) + (sim_new - old_mean) * (sim_new - new_mean)) / old_size) if old_size > 1 else 0.0

        # update cluster object
        cluster.embedding = new_embedding
        cluster.metadata.prototype_size = new_size
        cluster.metadata.mean_similarity = new_mean
        cluster.metadata.std_similarity = new_std
        cluster.metadata.label = cluster.metadata.label or Cluster.UNLABELLED
        cluster.label = cluster.label or Cluster.UNLABELLED
        self.clusters[cid] = cluster

        # update numpy arrays in-place
        self.cluster_embeddings[idx] = new_embedding
        self.prototype_sizes[idx] = new_size
        self.mean_sims[idx] = new_mean
        self.std_sims[idx] = new_std

        self.assignments[item_id] = cid

    def _active_slice(self):
        return slice(0, self._n)

    def cluster(self, ids: List[str], embeddings: List[np.ndarray], batch_size: Optional[int] = None):
        """
        Incrementally cluster items.
        - Uses in-place preallocated arrays to avoid expensive reallocations.
        - If batch_size is set (>1), scores are computed per batch against the current prototypes;
          assignments within a batch are still applied sequentially (keeps deterministic behavior).
        """
        emb_arr = np.asarray(embeddings, dtype=np.float64)
        if emb_arr.ndim == 1:
            emb_arr = emb_arr.reshape(-1, self.dim)
        n_items = emb_arr.shape[0]
        if emb_arr.shape[1] != self.dim:
            raise ValueError(f"embeddings dim {emb_arr.shape[1]} != expected {self.dim}")

        if batch_size is None or batch_size <= 1:
            # fully incremental (safe, deterministic)
            for item_id, emb in zip(ids, emb_arr):
                if self._n == 0:
                    self._add_cluster(item_id, emb)
                    continue

                # compute similarities to active prototypes only
                prot_embs = self.cluster_embeddings[self._active_slice()]  # view
                sims = prot_embs.dot(emb)  # shape: (n_clusters,)
                thresholds = self.mean_sims[self._active_slice()] + self.std_sims[self._active_slice()]
                valid_idx = np.nonzero(sims >= thresholds)[0]
                if valid_idx.size > 0:
                    best = valid_idx[np.argmax(sims[valid_idx])]
                    cid = self.cluster_ids[best]
                    self._update_cluster(item_id, emb, cid)
                else:
                    self._add_cluster(item_id, emb)
        else:
            # batch mode: compute sims matrix for each batch against current prototypes,
            # then apply assignments sequentially inside the batch (updates affect later items in batch).
            bs = int(batch_size)
            i = 0
            while i < n_items:
                j = min(i + bs, n_items)
                batch_embs = emb_arr[i:j]  # shape (b, dim)
                batch_ids = ids[i:j]

                if self._n == 0:
                    # quickly add the first item(s)
                    self._add_cluster(batch_ids[0], batch_embs[0])
                    start_idx = 1
                else:
                    start_idx = 0

                if self._n > 0 and start_idx < (j - i):
                    prot_embs = self.cluster_embeddings[self._active_slice()]  # (n_clusters, dim)
                    sims_mat = prot_embs.dot(batch_embs.T)  # (n_clusters, b)
                    thresholds = (self.mean_sims[self._active_slice()] + self.std_sims[self._active_slice()])[:, None]  # (n_clusters, 1)
                    # For each item in batch, choose best valid cluster based on current prototypes
                    for k in range(start_idx, j - i):
                        item_id = batch_ids[k]
                        emb = batch_embs[k]
                        sims = sims_mat[:, k]
                        valid_idx = np.nonzero(sims >= thresholds[:, 0])[0]
                        if valid_idx.size > 0:
                            best = valid_idx[np.argmax(sims[valid_idx])]
                            cid = self.cluster_ids[best]
                            self._update_cluster(item_id, emb, cid)
                            # after update, refresh the prototype row in sims_mat for remaining items in batch
                            prot_idx = best
                            # update sims_mat row prot_idx for remaining columns using updated prototype
                            if k + 1 < (j - i):
                                updated_proto = self.cluster_embeddings[prot_idx]
                                sims_mat[prot_idx, k + 1 :] = updated_proto.dot(batch_embs[k + 1 :].T)
                        else:
                            self._add_cluster(item_id, emb)

                # handle remaining items that were used to seed clusters if any (when _n==0)
                if self._n == 0 and (j - i) > 0:
                    # if still zero (very unlikely), add remaining sequentially
                    for k in range(start_idx, j - i):
                        self._add_cluster(batch_ids[k], batch_embs[k])

                i = j

        return self.clusters, self.assignments
