import pytest
import pytest_asyncio
from sereleum.data import get_dummy_data
from client.sereleum_client import SereleumClient
from httpx import HTTPStatusError
from smartscan import ClusterAccuracy

from sereleum.schemas.items.prompt import Prompt, PromptsOverviewInfo
from sereleum.schemas.api import  AddPromptsResponse

TEST_PROMPTS_FILE = "output/prompts/test_prompts.json"

@pytest_asyncio.fixture
async def setup_client():
    client = SereleumClient("http://127.0.0.1:8000")
    prompts = get_dummy_data(n=5)
    return client, prompts

@pytest.mark.asyncio
class TestReveliumClient:

    async def test_count_prompts(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        total_prompts = await client.count_prompts()
        assert isinstance(total_prompts, int)

    async def test_count_clusters(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        total_clusters = await client.count_clusters()
        assert isinstance(total_clusters, int)

    async def test_get_clusters(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        clusters = await client.get_clusters()
        assert isinstance(clusters, list)


    async def test_get_prompts(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, prompts = setup_client
        prompt_ids = [p.get("id") if isinstance(p, dict) else p.id for p in prompts]
        retrieved_prompts = await client.get_prompts(ids=prompt_ids)
        assert isinstance(retrieved_prompts, list)

    async def test_query_prompts(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        retrieved_prompts = await client.query_prompts("facts about physics", limit=10, cluster_ids=None)
        assert isinstance(retrieved_prompts, list)

    async def test_labels(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        labels = await client.get_existing_labels()
        assert isinstance(labels, list)


    async def test_update_cluster_label(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        label = "test label"

        try:
            update_result = await client.update_cluster_label(
                cluster_id="0173bc6fc4524fcaaee3f165410704f7",
                label=label,
            )
            assert update_result == label
        except HTTPStatusError as e:
            assert e.response.status_code == 404

    async def test_prompts_overview(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        overview = await client.get_prompts_overview()
        assert isinstance(overview, PromptsOverviewInfo)

    
    async def test_add_prompts_file(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        add_file_result = await client.add_prompts_file(TEST_PROMPTS_FILE, False)
        assert isinstance(add_file_result, AddPromptsResponse)
        async for event in  client.track_prompts_index_progress( add_file_result.job_id):
            pass
        
    # async def test_accuracy(self, setup_client: tuple[SereleumClient, list[Prompt]]):
    #     client, _ = setup_client
    #     accuracy = await client.get_cluster_accuracy()
    #     assert isinstance(accuracy, ClusterAccuracy)


    async def test_updated_prompt_cluster(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        try:
            test_prompt_id = "test_prompt_id"
            test_cluster_id = "test_cluster_id"
            new_id = await client.update_prompt_cluster_id(test_prompt_id, test_cluster_id)
            assert new_id == test_cluster_id
        except HTTPStatusError as e:
            assert e.response.status_code == 404

    async def test_get_cluster_plot(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        count = await client.count_clusters()
        img_bytes = await client.get_cluster_plot()

        if count == 0:
            assert img_bytes == None
        else:
            assert isinstance(img_bytes, bytes)

    
    async def test_merge_clusters(self, setup_client: tuple[SereleumClient, list[Prompt]]):
        client, _ = setup_client
        try:
            merges = {}
            updated_clusters = await client.merge_clusters(merges)
            assert isinstance(updated_clusters, list)
        except HTTPStatusError as e:
            assert e.response.status_code == 400
            data = e.response.json() 
            assert data["detail"] == "Merges cannot be empty"