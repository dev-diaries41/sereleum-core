import numpy as np
import math
import uuid

from sqlalchemy.exc import IntegrityError

from numpy.typing import NDArray
from typing import List, Dict, Generic

from smartscan import Cluster, ClusterMetadata, ClusterMerges, ClusterId, StoredEmbedding, ClusterResult, Assignments
from smartscan.embeds import EmbeddingStore, generate_prototype_embedding
from smartscan.cluster import IncrementalClusterer

from sereleum.schemas.cluster import ClusterCrossRef, StoredClusterMetadata
from sereleum.errors import SereleumError, ErrorCode
from sereleum.data.stores.item_store import ItemStore
from sereleum.data.stores.clusters.cluster_store import ClusterStore
from sereleum.data.stores.clusters.cluster_crossref_store import ClusterCrossRefStore
from sereleum.data.types import TItem, TCollection
from sereleum.collections.collecion_manager import CollectionManager
from sereleum.label.cluster_labeller import ClusterLabeller

class ClusterManager(Generic[TItem, TCollection], CollectionManager[TCollection]):
    def __init__(
        self, 
        cluster_store: ClusterStore,
        crossrefs_store: ClusterCrossRefStore,
        cluster_embedding_store: EmbeddingStore,
        item_store: ItemStore[TItem],
        item_embedding_store: EmbeddingStore,
        labeller: ClusterLabeller | None = None
        ): 
        self.cluster_embedding_store = cluster_embedding_store 
        self.cluster_store = cluster_store
        self.crossrefs_store = crossrefs_store 
        self.item_store = item_store
        self.item_embedding_store = item_embedding_store
        self.labeller = labeller

            
    async def cluster(self, auto_label: bool = True, default_threshold: float = 0.3) -> ClusterResult:
        uncluster_embeds = await self._get_unclustered_items()
        if not uncluster_embeds: return ClusterResult()
        existing_clusters = await self._get_existing_clusters()
        ## TODO: sample run to get default threshold if existing clusters dont exist
        threshold = self._get_default_threshold(existing_clusters) if existing_clusters else default_threshold
        clusterer = IncrementalClusterer(
            default_threshold=threshold,
            existing_clusters=existing_clusters,
        )
        result = clusterer.cluster(uncluster_embeds)
        unlabelled_clusters = await self._update_clusters_and_assisgn(result, set(existing_clusters.keys()))
        if len(unlabelled_clusters) > 0 and auto_label and self.labeller:
           await self.label(unlabelled_clusters)
        return result

    async def rebuild_clusters(self, auto_label: bool = True, default_threshold: float = 0.3) -> ClusterResult:
        await self.cluster_store.clear()
        await self.cluster_embedding_store.clear()
        return await self.cluster(auto_label, default_threshold)

    async def move(
        self,
        destination_collection_id: str,
        source_collection_id: str,
        item_ids: list[str] | None,
        *,
        select_all: bool = False,
        excluded_item_ids: list[str] | None = None,
    ) -> None:
        try:
            await self.crossrefs_store.move(
                destination_collection_id=destination_collection_id,
                item_ids=item_ids,
                select_all=select_all,
                excluded_item_ids=excluded_item_ids,
                source_collection_id=source_collection_id,
            )
            await self._sync(source_collection_id)
        except IntegrityError as e:
            raise SereleumError(
                "Foreign key violation in assign",
                code=ErrorCode.INVALID_ARGUMENT,
                details={"error": str(e)},
            )


    async def delete(self, collection_ids: list[str]):
        await self.cluster_store.delete_by_ids(collection_ids)
        await self.cluster_embedding_store.delete(collection_ids)

    async def rename(self, collection_id: str, name) -> None:
        result = await self.cluster_store.get(filter={'ids': [collection_id]})
        if(len(result)) == 0:
            raise SereleumError(
                "Cluster not found",
                code=ErrorCode.CLUSTER_NOT_FOUND,
            )
        metadata=result[0]
        metadata.label = name

        try:
            await self.cluster_store.update([metadata])
        except IntegrityError as e:
            raise SereleumError(
                    "Cluster label already exists",
                    code=ErrorCode.DUPLICATE_NAME,
                    details={"error": str(e)},
                ) from None


    async def get_collections(
        self,
        filter = None,
        limit = None,
        offset = 0,
        order_by = None,
        ascending = False
    ) -> List[TCollection]:
       return await self.cluster_store.get_collections(
            filter=filter,
            limit=limit,
            offset=offset,
            order_by=order_by,
            ascending=ascending
            )


    async def merge(self, primary_collection_id: str, secondary_collection_ids: list[str]) -> None:
        merges: ClusterMerges = {primary_collection_id: secondary_collection_ids}
        await self._assign_from_merges(merges)
        merged_clustered_ids = {cid for targets in merges.values() for cid in targets}
        await self.cluster_embedding_store.delete(list(merged_clustered_ids)) 
        await self.cluster_store.delete_by_ids(list(merged_clustered_ids)) 

        cluster_metadata_updates: list[StoredClusterMetadata] = []
        cluster_embed_updates: list[StoredEmbedding] = []

        for merge_id in merges.keys():
            if sync_result := await self._sync(merge_id):
                stored_embed, meta = sync_result
                cluster_embed_updates.append(stored_embed)
                cluster_metadata_updates.append(meta)
            
        await self.cluster_embedding_store.update(cluster_embed_updates)
        await self.cluster_store.update(cluster_metadata_updates)


    async def label(self, cluster_ids: list[str]) -> None:
        if not self.labeller:
            raise ValueError("Missing cluster labeller")
        cluster_samples = {cluster_id : await self._get_cluster_samples(cluster_id) for cluster_id in cluster_ids}
        labelled_clusters = await self.labeller.label_clusters(cluster_samples)
        await self.cluster_store.update_labels(labelled_clusters)


    async def create(self, name: str, seed: NDArray) -> str:
        try:
            cluster_embed = StoredEmbedding(item_id=self._generate_id(), embedding=seed)
            cluster_meta = StoredClusterMetadata(
                id=cluster_embed.item_id,
                label=name,
                prototype_size=1,
                std_similarity=0.0,
                mean_similarity=0.3 # default threshold
            )
            await self.cluster_store.add([cluster_meta])
            await self.cluster_embedding_store.add([cluster_embed])
            return cluster_meta.id
        except IntegrityError as e:
            raise SereleumError(
                    "Cluster label already exists",
                    code=ErrorCode.DUPLICATE_NAME,
                    details={"error": str(e)},
                ) from None
   
    async def clear(self):
        await self.cluster_store.clear()
        await self.cluster_embedding_store.clear()

    async def _assign(self, assignments: Assignments) -> None:        
        crossrefs = [ClusterCrossRef(item_id=item_id, cluster_id=cluster_id) for item_id, cluster_id in assignments.items()]
        try:
            await self.crossrefs_store.upsert(crossrefs)
        except IntegrityError as e:
            raise SereleumError(
                    "Foreign key violation in assign",
                    code=ErrorCode.ITEM_OR_CLUSTER_NOT_FOUND,
                    details={"error": str(e)},
                ) from None

    async def _assign_from_merges(self, merges: ClusterMerges) -> None:
        all_target_cluster_ids = [cid for targets in merges.values() for cid in targets]
        cross_refs: list[ClusterCrossRef] = []

        for crossref in await self.crossrefs_store.get(filter={'include_cluster_ids': all_target_cluster_ids}):
            original_cluster = crossref.cluster_id
            new_cluster_id = next(
                (mid for mid, clusters in merges.items()
                if original_cluster in clusters),
                original_cluster,
            )
            crossref.cluster_id = new_cluster_id
            cross_refs.append(crossref)

        await self.crossrefs_store.update(cross_refs)

    # MUST update clusters firsts before assignments!!!
    async def _update_clusters_and_assisgn(self, result: ClusterResult, existing_clusters_ids: set[str]) -> list[str]:
        new_cluster_metadata_updates: list[StoredClusterMetadata] = []
        existing_cluster_metadata_updates: list[StoredClusterMetadata] = []
        new_cluster_embed_updates: list[StoredEmbedding] = []
        existing_cluster_embed_updates: list[StoredEmbedding] = []
        unlabelled_cluster_ids: list[str] = []

        for cluster in result.clusters.values():
            updated_meta = StoredClusterMetadata(
                id=cluster.prototype_id,
                prototype_size=cluster.metadata.prototype_size,
                mean_similarity=cluster.metadata.mean_similarity,
                std_similarity=cluster.metadata.std_similarity,
                label = cluster.metadata.label,
            )
            stored_embed = StoredEmbedding(item_id=updated_meta.id, embedding=cluster.embedding)

            if updated_meta.id in existing_clusters_ids:
                existing_cluster_embed_updates.append(stored_embed)
                existing_cluster_metadata_updates.append(updated_meta)
            else:
                new_cluster_embed_updates.append(stored_embed)
                new_cluster_metadata_updates.append(updated_meta)
            
            if not cluster.metadata.label:
                unlabelled_cluster_ids.append(updated_meta.id)
             
        await self.cluster_store.update(existing_cluster_metadata_updates)
        await self.cluster_store.add(new_cluster_metadata_updates)
        await self.cluster_embedding_store.update(existing_cluster_embed_updates)
        await self.cluster_embedding_store.add(new_cluster_embed_updates)
        await self._assign(result.assignments)
        return unlabelled_cluster_ids

    async def _sync(self, cluster_id: ClusterId) -> tuple[StoredEmbedding, StoredClusterMetadata] | None:
        result = await self.cluster_store.get(filter={'ids': [cluster_id]})
        if len(result) == 0:
            return None
        crossrefs = await self.crossrefs_store.get(filter={'include_cluster_ids': [cluster_id]})
        
        if len(crossrefs) == 0:
            await self.cluster_store.delete_by_ids([cluster_id])
            return None
        item_ids = [c.item_id for c in crossrefs]

        embeds = await self.item_embedding_store.get(ids=item_ids)
        new_protoype_embed, new_mean_sim, new_std_sim = self._compute_cluster_metrics(np.stack([e.embedding for e in embeds], axis=0))
        
        old_cluster_metadata = result[0]
        new_meta = StoredClusterMetadata(
            id = old_cluster_metadata.id,
            prototype_size=len(embeds),
            mean_similarity=new_mean_sim,
            std_similarity=new_std_sim,
            label = old_cluster_metadata.label
            )
        stored_embed = StoredEmbedding(item_id=new_meta.id, embedding=new_protoype_embed)
        return stored_embed, new_meta
    
    async def _get_unclustered_items(self) -> Dict[str, NDArray]:
        unclustered_items_ids = await self.cluster_store.get_unclustered_item_ids()
        if len(unclustered_items_ids) == 0:
            return {}
        unclustered_item_embeds  = await self.item_embedding_store.get(unclustered_items_ids)
        return {emb.item_id: emb.embedding for emb in unclustered_item_embeds}

    def _compute_cluster_metrics(self, embeds: List[NDArray]):
        new_protoype_embed = generate_prototype_embedding(embeds)
        sims = np.dot(embeds, new_protoype_embed)
        new_mean_sim = float(np.mean(sims))
        new_std_sim = math.sqrt(np.mean([(float(sim) - new_mean_sim)**2 for sim in sims]))
        return new_protoype_embed, new_mean_sim, new_std_sim

    def _get_default_threshold(self, existing_clusters: dict[ClusterId, Cluster]) -> float:
        return float(np.mean([(c.metadata.mean_similarity - c.metadata.std_similarity) for c in existing_clusters.values()]))

    async def _get_cluster_samples(self, cluster_id: str, sample_size: int = 10)-> list[str]:
        result = await self.cluster_embedding_store.get([cluster_id])
        if len(result) == 0:
            raise ValueError("Cluster not found")
        
        cluster_embed = result[0]
        crossrefs = await self.crossrefs_store.get(filter={'include_cluster_ids': [cluster_id]})
        ids = [c.item_id for c in crossrefs]
        query_result = await self.item_embedding_store.query(query_embed=cluster_embed.embedding, ids=ids, topK=sample_size)
        samples = [item.content for item in await self.item_store.get(filter={'ids': query_result.ids})]
        return samples

    @staticmethod
    def _generate_id() -> str:
        return uuid.uuid4().hex

    async def _get_existing_clusters(self) -> dict[ClusterId, Cluster]:
        all_meta = await self.cluster_store.get()
        all_cluster_embeds = {emb.item_id : emb for emb in await self.cluster_embedding_store.get()}
        existing_clusters = { meta.id: Cluster(
            prototype_id=meta.id,
            embedding=all_cluster_embeds[meta.id].embedding,
            metadata=ClusterMetadata(
                prototype_size=meta.prototype_size,
                mean_similarity=meta.mean_similarity,
                std_similarity=meta.std_similarity,
                label=meta.label
                )
            ) for meta in all_meta
        }
        return existing_clusters