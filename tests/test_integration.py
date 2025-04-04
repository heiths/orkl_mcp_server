"""Integration tests for the ORKL MCP server."""

import pytest

from orkl_mcp.api_client import OrklApiClient
from orkl_mcp.config import OrklConfig


@pytest.fixture
def config():
    """Create a test configuration."""
    return OrklConfig(
        api_base_url="https://orkl.eu/api/v1",
        request_timeout=30,
        cache_ttl=300,
        use_cache=True,
        rate_limit_requests=90,
        rate_limit_period=30,
    )


@pytest.fixture
def client(config):
    """Create a test API client."""
    return OrklApiClient(config)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_library_info(client):
    """Test getting library information."""
    result = await client.get_library_info()
    assert result["status"] == "success"
    assert "data" in result
    assert "library_entries" in result["data"]
    assert "library_version" in result["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_library_version(client):
    """Test getting library version information."""
    result = await client.get_library_version()
    assert result["status"] == "success"
    assert "data" in result
    assert "ID" in result["data"]
    assert "CreatedAt" in result["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_library_entries(client):
    """Test getting library entries."""
    result = await client.get_library_entries(limit=5)
    assert result["status"] == "success"
    assert "data" in result
    assert isinstance(result["data"], list)
    assert len(result["data"]) <= 5
    for entry in result["data"]:
        assert "id" in entry
        assert "title" in entry
        assert "created_at" in entry


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_library_entry(client):
    """Test getting a specific library entry."""
    # First get a list of entries to find a valid ID
    entries_result = await client.get_library_entries(limit=1)
    assert entries_result["status"] == "success"
    assert "data" in entries_result
    assert len(entries_result["data"]) > 0
    entry_id = entries_result["data"][0]["id"]
    
    # Now get the specific entry
    result = await client.get_library_entry(entry_id)
    assert result["status"] == "success"
    assert "data" in result
    assert result["data"]["id"] == entry_id
    assert "title" in result["data"]
    assert "file_creation_date" in result["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_library(client):
    """Test searching the library."""
    result = await client.search_library("test", limit=5)
    assert result["status"] == "success"
    assert "data" in result
    assert isinstance(result["data"], list)
    assert len(result["data"]) <= 5
    for entry in result["data"]:
        assert "id" in entry
        assert "title" in entry


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_source_entries(client):
    """Test getting source entries."""
    result = await client.get_source_entries()
    assert result["status"] == "success"
    assert "data" in result
    assert isinstance(result["data"], list)
    assert len(result["data"]) > 0
    for entry in result["data"]:
        assert "id" in entry
        assert "description" in entry


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_source_entry(client):
    """Test getting a specific source entry."""
    # First get a list of sources to find a valid ID
    sources_result = await client.get_source_entries()
    assert sources_result["status"] == "success"
    assert "data" in sources_result
    assert len(sources_result["data"]) > 0
    source_id = sources_result["data"][0]["id"]
    
    # Now get the specific source
    result = await client.get_source_entry(source_id)
    assert result["status"] == "success"
    assert "data" in result
    assert result["data"]["id"] == source_id
    assert "description" in result["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_ta_entries(client):
    """Test getting threat actor entries."""
    result = await client.get_threat_actor_entries()
    assert result["status"] == "success"
    assert "data" in result
    assert isinstance(result["data"], list)
    assert len(result["data"]) > 0
    for entry in result["data"]:
        assert "id" in entry
        assert "aliases" in entry


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_ta_entry(client):
    """Test getting a specific threat actor entry."""
    # First get a list of threat actors to find a valid ID
    tas_result = await client.get_threat_actor_entries()
    assert tas_result["status"] == "success"
    assert "data" in tas_result
    assert len(tas_result["data"]) > 0
    ta_id = tas_result["data"][0]["id"]
    
    # Now get the specific threat actor
    result = await client.get_threat_actor_entry(ta_id)
    assert result["status"] == "success"
    assert "data" in result
    assert result["data"]["id"] == ta_id
    assert "aliases" in result["data"]
