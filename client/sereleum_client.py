from typing import List, Optional
import httpx
import json

from smartscan import ClusterMerges

from sereleum.schemas.cluster import StoredClusterMetadata
from sereleum.schemas.items.prompt import Prompt, PromptsOverviewInfo
from sereleum.constants.api import Routes
from sereleum.schemas.api import  GetPromptsRequest, GetPromptsByIdsRequest, GetClusterRequestParams, UpdateLabelParams, QueryPromptsRequest, UpdatePromptClusterIdParams, AddPromptsResponse, MergeClustersRequest, ClusterOptionsForm

class SereleumClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
    
    async def add_prompts_file(self, file_path: str, auto_label: bool = True, default_threshold: float = 0.55) -> AddPromptsResponse:
        """
        Upload a JSON file containing prompts.
        """
        url = f"{self.base_url}{Routes.ADD_PROMPTS_FILE_ENDPOINT}"
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {"file": (file_path, f, "application/json")}
                res = await client.post(url, files=files, data=ClusterOptionsForm(auto_label=auto_label, default_threshold=default_threshold).model_dump())
            res.raise_for_status() 
            return AddPromptsResponse(**res.json())
        
    async def get_prompts(self, cluster_ids: Optional[List[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Prompt]:
        url = f"{self.base_url}{Routes.BASE_PROMPTS_ENDPOINT}"
        payload = GetPromptsRequest(cluster_ids=cluster_ids, limit=limit, offset=offset)

        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload.model_dump())
            res.raise_for_status() 
            return [Prompt(**p) for p in res.json().get('prompts', [])]
        
    async def get_prompts_by_ids(self, ids: List[str]) -> List[Prompt]:
        url = f"{self.base_url}{Routes.BASE_PROMPTS_ENDPOINT}"
        payload = GetPromptsByIdsRequest(prompt_ids=ids)

        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload.model_dump())
            res.raise_for_status() 
            return [Prompt(**p) for p in res.json().get('prompts', [])]
        
        
    async def query_prompts(self, query: str, cluster_ids: Optional[List[str]] = None, limit: Optional[int] = None) -> List[Prompt]:
        url = f"{self.base_url}{Routes.QUERY_PROMPTS_ENDPOINT}"
        payload = QueryPromptsRequest(query=query, cluster_ids=cluster_ids, limit=limit)

        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload.model_dump())
            res.raise_for_status() 
            return [Prompt(**p) for p in res.json().get('prompts', [])]
        
        
    async def get_prompts_overview(self) -> PromptsOverviewInfo:
        url = f"{self.base_url}{Routes.GET_PROMPTS_OVERVIEW_ENDPOINT}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            res.raise_for_status() 
            return PromptsOverviewInfo(**res.json())

    async def update_prompt_cluster_id(self, prompt_id: str, cluster_id: str) -> str:
        url = f"{self.base_url}{Routes.BASE_PROMPTS_ENDPOINT}"
        payload = UpdatePromptClusterIdParams(prompt_id=prompt_id, cluster_id=cluster_id)
        async with httpx.AsyncClient() as client:
            res = await client.patch(url, params=payload.model_dump())
            res.raise_for_status() 
            return res.json().get("updated_cluster_id")


    async def get_clusters(self, cluster_id: Optional[str] = None, limit: Optional[str] = None, offset: Optional[str] = None ) -> List[StoredClusterMetadata]:
        url = f"{self.base_url}{Routes.BASE_CLUSTER_ENDPOINT}"
        params = GetClusterRequestParams(cluster_id=cluster_id, limit=limit, offset=offset)

        async with httpx.AsyncClient() as client:
            res = await client.get(url, params=params.model_dump())
            res.raise_for_status() 
            return [StoredClusterMetadata(**c) for c in res.json().get('clusters', [])]
        

    async def update_cluster_label(self, cluster_id: str, label: str) -> str:
        url = f"{self.base_url}{Routes.BASE_CLUSTER_ENDPOINT}"
        params = UpdateLabelParams(cluster_id=cluster_id, label=label)

        async with httpx.AsyncClient() as client:
            res = await client.patch(url, params=params.model_dump())
            res.raise_for_status() 
            return res.json().get("updated_label")
        
    async def count_prompts(self) -> int:
        url = f"{self.base_url}{Routes.COUNT_PROMPTS_ENDPOINT}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            res.raise_for_status() 
            return res.json().get("count", 0)

   
    async def count_clusters(self) -> int:
        url = f"{self.base_url}{Routes.COUNT_CLUSTERS_ENDPOINT}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            res.raise_for_status() 
            return res.json().get("count", 0)


    async def get_cluster_plot(self) -> Optional[bytes]:
        url = f"{self.base_url}{Routes.GET_CLUSTER_PLOT_ENDPOINT}"
        # params = {"method": method}

        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            print(res.status_code)
            if res.status_code == 204:
                return None

            res.raise_for_status()
            return res.content 
        
    async def merge_clusters(self, merges: ClusterMerges) -> List[StoredClusterMetadata]:
        url = f"{self.base_url}{Routes.MERGE_CLUSTERS_ENDPOINT}"
        payload = MergeClustersRequest(merges=merges)

        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload.model_dump())
            res.raise_for_status() 
            return [StoredClusterMetadata(**c) for c in res.json().get('updated_clusters', [])]
        
        
    async def track_prompts_index_progress(self, job_id: str):
        url = f"{self.base_url}/{Routes.SSE_PROMPTS_INDEX_PROGRESS}?job_id={job_id}"

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url) as response:
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        yield json.loads(data_str)

    async def track_prompts_cluster_status(self, job_id: str):
        url = f"{self.base_url}/{Routes.SSE_PROMPTS_CLUSTER_STATUS}?job_id={job_id}"

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url) as response:
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        yield json.loads(data_str)

