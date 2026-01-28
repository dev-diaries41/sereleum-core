import numpy as np
import random
import uuid

from typing import Dict, List, Optional
from smartscan.classify.helpers import merge_similar_clusters
from smartscan.classify.types import (
    Cluster,
    Assignments,
    ClusterMetadata,
    ClusterResult,
)
from smartscan.embeds import update_prototype_embedding


class IncrementalClusterer:
    def __init__(
        self,
        existing_clusters: Optional[Dict[str, Cluster]] = None,
        existing_assignments: Optional[Assignments] = None,
        default_threshold: float = 0.3,
        merge_threshold: Optional[float] = None,
        min_cluster_size: int = 2,
        top_k: int = 3,
        benchmarking: bool = False,
    ):

        self.clusters: Dict[str, Cluster] = existing_clusters or {}
        self.assignments: Assignments = existing_assignments or {}
        
        # incremental count map for cluster sizes
        self._counts: Dict[str, int] = {cid: 0 for cid in self.clusters}
        for cid in self.assignments.values():
            if cid in self._counts:
                self._counts[cid] += 1
        cohesions = [c.metadata.mean_similarity for c in self.clusters.values()]
        min_cohesion = np.percentile(cohesions, 1) if cohesions else 0.0
        self.default_threshold = max(default_threshold, min_cohesion)
        self.min_cluster_size = min_cluster_size
        self.top_k = top_k
        self.merge_threshold = merge_threshold
        self.benchmarking = benchmarking

    def _compute_min_cluster_size(self, total_items: int) -> int:
        if total_items <= 0:
            return max(2, self.min_cluster_size)
        adaptive = max(2, int(np.sqrt(total_items)))
        return max(adaptive, self.min_cluster_size)

    def _get_threshold(self, cluster: Cluster, avg_cohesion: float, avg_cluster_size: float, min_cluster_size: int) -> float:
        mean_sim = cluster.metadata.mean_similarity
        std_sim = cluster.metadata.std_similarity
        cluster_size = cluster.metadata.prototype_size
        
        size_factor = cluster_size / max(1, avg_cluster_size)        
        baseline = self.default_threshold + std_sim

         # immature clusters: always loose
        if cluster_size < min_cluster_size or avg_cohesion <= 0:
            return max(baseline - std_sim, 0.0)
        x = (mean_sim - avg_cohesion) / max(1e-6, avg_cohesion)
        alpha = 1.0 / (1.0 + np.exp(-x))
        mean_candidate = mean_sim if mean_sim > baseline else baseline
        base_candidate = alpha * mean_candidate + (1.0 - alpha) * baseline
        return max(base_candidate - std_sim, 0.0) * size_factor

    def cluster(self, ids: List[str], embeddings: List[np.ndarray]) -> ClusterResult:
        items: Dict[str, np.ndarray] = {i: e for i, e in zip(ids, embeddings)}
        all_items = items.copy()
        min_cluster_size = self._compute_min_cluster_size(len(all_items))

        while items:
            item_id = sorted(items.keys())[0]
            emb = items.pop(item_id)

            if not self.clusters:
                self._set_and_assign(item_id, emb)
                continue

            cluster_ids = list(self.clusters.keys())
            cos_sims = np.array([np.dot(emb, self.clusters[cid].embedding) for cid in cluster_ids])
            cohesions, cluster_sizes = [], []

            for c in self.clusters.values():
                cluster_sizes.append(c.metadata.prototype_size)
                if c.metadata.prototype_size > 1:
                    cohesions.append(c.metadata.mean_similarity)

            avg_cohesion = np.mean(cohesions) if cohesions else 0.0
            avg_cluster_size = np.mean(cluster_sizes) if cluster_sizes else 0.0
            thresholds = np.array([self._get_threshold(self.clusters[cid], avg_cohesion, avg_cluster_size, min_cluster_size) for cid in cluster_ids])

            valid_idx = np.where(cos_sims >= thresholds)[0]
            if valid_idx.size > 0:
                best_idx = valid_idx[np.argmax(cos_sims[valid_idx])]
                self._update_and_assign(item_id, emb, self.clusters[cluster_ids[best_idx]])
            else:
                prev_cid = self.assignments.get(item_id)
                if prev_cid and prev_cid in self.clusters:
                    # DO NOT create new cluster if it is already in one
                    pass
                else:
                    # truly new item
                    self._set_and_assign(item_id, emb)


        def _current_avg_cohesion():
            cs = [c.metadata.mean_similarity for c in self.clusters.values() if c.metadata.prototype_size > 1]
            return float(np.mean(cs)) if cs else 0.0

        # Reassignment phase: extend previous "small cluster" logic to consider ALL clusters.
        # Termination conditions: loop until either (a) no progressed changes in an iteration, or
        # every item's assigned cluster equals the cluster with maximum similarity (i.e. stable).
        
        while True:
            if not self.clusters:
                break

            avg_cohesion = _current_avg_cohesion()
            candidate_clusters = {cid: c for cid, c in self.clusters.items()}
            progressed = False

            for sid, cluster in list(candidate_clusters.items()):
                other_item_ids = [item_id for item_id in all_items.keys() if item_id not in self.assignments or self.assignments.get(item_id) != sid]
                if not other_item_ids:
                    continue

                other_embeds = np.array([all_items[oid] for oid in other_item_ids])
                sims = np.dot(other_embeds, cluster.embedding)
                k = min(5, len(sims))
                if k == 0:
                    continue
                top_idx = np.argpartition(-sims, k - 1)[:k] if len(sims) > k else np.argsort(-sims)
                top_idx = top_idx[np.argsort(-sims[top_idx])] if len(sims) > k else top_idx
                top_item_ids = [other_item_ids[i] for i in top_idx]

                vote_counts, vote_sims = {}, {}
                for tid in top_item_ids:
                    tid_cid = self.assignments.get(tid)
                    if tid_cid and tid_cid in self.clusters:
                        vote_counts[tid_cid] = vote_counts.get(tid_cid, 0) + 1
                        vote_sims.setdefault(tid_cid, []).append(float(np.dot(cluster.embedding, self.clusters[tid_cid].embedding)))

                total_votes = sum(vote_counts.values())
                majority_needed = (k // 2) + 1
                other_votes = total_votes - vote_counts.get(sid, 0)
               
                # cluster is eligible for reassignment only if majority of top-k neighbors belong to other clusters
                if other_votes < majority_needed:
                    continue

                top_vote_value = max(vote_counts.values())
                candidate_cids = [cid for cid, v in vote_counts.items() if v == top_vote_value]
                chosen_target_cid = candidate_cids[0] if len(candidate_cids) == 1 else max(candidate_cids, key=lambda cid: float(np.mean(vote_sims.get(cid, [0.0]))))
                if chosen_target_cid == sid:
                    continue

                target_cluster = self.clusters.get(chosen_target_cid)
                if not target_cluster:
                    continue

                reassigned_items = [item_id for item_id, cid in self.assignments.items() if cid == sid]

                for item_id in reassigned_items:
                    item_emb = all_items[item_id]
                    other_ids = [oid for oid in all_items if oid != item_id and oid in self.assignments]
                    if not other_ids:
                        self._update_and_assign(item_id, item_emb, target_cluster)
                        progressed = True
                        continue

                    other_embs = np.array([all_items[oid] for oid in other_ids])
                    nn_dists = np.dot(other_embs, item_emb)
                    nn_idx = np.argpartition(-nn_dists, self.top_k - 1)[:self.top_k] if len(nn_dists) > self.top_k else np.argsort(-nn_dists)[::-1]

                    votes, sims_map = {}, {}
                    for idx in nn_idx:
                        nid = other_ids[idx]
                        cid = self.assignments.get(nid)
                        if cid and cid in self.clusters:
                            votes[cid] = votes.get(cid, 0) + 1
                            sims_map.setdefault(cid, []).append(float(np.dot(item_emb, self.clusters[cid].embedding)))

                    if not votes:
                        self._update_and_assign(item_id, item_emb, self.clusters[sid])
                        continue

                    top_clusters = [cid for cid, v in votes.items() if v == max(votes.values())]
                    chosen_cid = top_clusters[0] if len(top_clusters) == 1 else max(top_clusters, key=lambda cid: float(np.mean(sims_map.get(cid, [0.0]))))
                    self._update_and_assign(item_id, item_emb, self.clusters[chosen_cid])
                    if chosen_cid != sid:
                        progressed = True

            # Remove empty clusters
            empty_clusters = [cid for cid in self.clusters if cid not in self.assignments.values()]
            for cid in empty_clusters:
                del self.clusters[cid]

            # Check global stability: every item should be assigned to the cluster with highest similarity
            # If that holds, clusters are stable and can stop. Also stop if no changes were made in this iteration.
            cluster_ids = list(self.clusters.keys())
            cluster_embs = np.array([c.embedding for c in self.clusters.values()]) if self.clusters else np.array([])
            stable_all = True
            if cluster_embs.size > 0:
                for item_id, emb in all_items.items():
                    if item_id not in self.assignments:
                        stable_all = False
                        break
                    sims = np.dot(cluster_embs, emb)
                    best_idx = int(np.argmax(sims))
                    best_cid = cluster_ids[best_idx]
                    if self.assignments.get(item_id) != best_cid:
                        stable_all = False
                        break

            if stable_all or not progressed:
                break

        cluster_merges = None
        if self.merge_threshold:
            cluster_merges = merge_similar_clusters(self.clusters, self.merge_threshold)

        return ClusterResult(self.clusters, self.assignments, cluster_merges)

    def clear(self):
        self.clusters.clear()
        self.assignments.clear()
        self._counts.clear()

    def _set_and_assign(self, item_id: str, embedding: np.ndarray):
        prototype_id = self._generate_id()
        metadata = ClusterMetadata(prototype_size=1, mean_similarity=self.default_threshold, std_similarity=0.0, label=Cluster.UNLABELLED)
        cluster = Cluster(prototype_id, embedding, metadata, label=Cluster.UNLABELLED)
        self.clusters[prototype_id] = cluster
        self.assignments[item_id] = prototype_id
        self._counts[prototype_id] = 1

    def _update_and_assign(self, item_id: str, embedding: np.ndarray, cluster: Cluster):
        target_cid = cluster.prototype_id
        prev_cid = self.assignments.get(item_id)

        if prev_cid == target_cid:
            return

        old_size = self._counts.get(target_cid, 0)
        old_meta = cluster.metadata
        new_embedding = update_prototype_embedding(cluster.embedding, embedding, old_size)
        sim_new = float(np.dot(new_embedding, embedding))
        new_mean = (old_meta.mean_similarity * old_size + sim_new) / (old_size + 1) if old_size >= 1 else sim_new
        new_std = (np.sqrt(((old_size - 1) * old_meta.std_similarity**2 + (sim_new - old_meta.mean_similarity) * (sim_new - new_mean)) / old_size)
                   if old_size > 1 else 0.0)

        self.clusters[target_cid] = Cluster(
            target_cid,
            new_embedding,
            metadata=ClusterMetadata(
                prototype_size=old_size + 1,
                mean_similarity=new_mean,
                std_similarity=new_std,
                label=cluster.label,
            ),
            label=cluster.label,
        )

        # update assignments
        self.assignments[item_id] = target_cid

        # update incremental counts
        self._counts[target_cid] = old_size + 1

        if prev_cid and prev_cid != target_cid:
            prev_count = self._counts.get(prev_cid, 0) - 1
            if prev_count <= 0:
                if prev_cid in self.clusters:
                    del self.clusters[prev_cid]
                self._counts.pop(prev_cid, None)
            else:
                self._counts[prev_cid] = prev_count
                prev_cluster = self.clusters[prev_cid]
                prev_meta = prev_cluster.metadata
                self.clusters[prev_cid] = Cluster(
                    prev_cluster.prototype_id,
                    prev_cluster.embedding,
                    metadata=ClusterMetadata(
                        prototype_size=prev_count,
                        mean_similarity=prev_meta.mean_similarity,
                        std_similarity=prev_meta.std_similarity,
                        label=prev_meta.label,
                    ),
                    label=prev_cluster.label,
                )


    def _generate_id(self):
        return random.randbytes(8).hex() if self.benchmarking else uuid.uuid4().hex
