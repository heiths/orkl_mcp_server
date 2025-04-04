"""Tests for the ORKL MCP server."""

import pytest
from unittest import mock
from mcp.server.fastmcp import FastMCP

from orkl_mcp.api_client import OrklApiClient
from orkl_mcp.config import OrklConfig
from orkl_mcp.server import (
    app_lifespan,
    fetch_latest_threat_reports,
    fetch_threat_report_details,
    search_threat_reports,
    get_library_info,
    get_library_version,
    fetch_threat_actors,
    fetch_threat_actor_details,
    fetch_sources,
    fetch_source_details,
    clear_cache,
)


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
def api_client(config):
    """Create a mock API client."""
    client = mock.MagicMock(spec=OrklApiClient)
    client.get_library_info = mock.AsyncMock(return_value={
        "data": {
            "name": "Test Library",
            "version": "1.0.0",
            "entries": 100
        }
    })
    client.get_library_version = mock.AsyncMock(return_value={
        "data": {
            "version": "1.0.0",
            "build_date": "2024-01-01"
        }
    })
    client.get_library_entries = mock.AsyncMock(return_value={
        "data": [
            {"uuid": "test1", "title": "Test 1", "created_at": "2024-01-01"},
            {"uuid": "test2", "title": "Test 2", "created_at": "2024-01-02"}
        ]
    })
    client.get_library_entry = mock.AsyncMock(return_value={
        "data": {
            "uuid": "test1",
            "title": "Test 1",
            "content": "Test content",
            "created_at": "2024-01-01"
        }
    })
    client.search_library = mock.AsyncMock(return_value={
        "data": [
            {"uuid": "test1", "title": "Test 1"},
            {"uuid": "test2", "title": "Test 2"}
        ]
    })
    client.get_source_entries = mock.AsyncMock(return_value={
        "data": [
            {"uuid": "source1", "name": "Source 1"},
            {"uuid": "source2", "name": "Source 2"}
        ]
    })
    client.get_source_entry = mock.AsyncMock(return_value={
        "data": {
            "uuid": "source1",
            "name": "Source 1",
            "description": "Test source"
        }
    })
    client.get_threat_actor_entries = mock.AsyncMock(return_value={
        "data": [
            {"uuid": "ta1", "name": "TA 1"},
            {"uuid": "ta2", "name": "TA 2"}
        ]
    })
    client.get_threat_actor_entry = mock.AsyncMock(return_value={
        "data": {
            "uuid": "ta1",
            "name": "TA 1",
            "description": "Test TA"
        }
    })
    return client


@pytest.fixture
def ctx(api_client, config):
    """Create a test context."""
    return type("Context", (), {
        "request_context": type("RequestContext", (), {
            "lifespan_context": type("LifespanContext", (), {
                "api_client": api_client,
                "config": config
            })()
        })()
    })


@pytest.mark.asyncio
async def test_app_lifespan(config):
    """Test application lifespan."""
    server = FastMCP()
    async with app_lifespan(server) as context:
        assert context.api_client is not None
        assert isinstance(context.config, OrklConfig)
        assert context.config.api_base_url == config.api_base_url
        assert context.config.request_timeout == config.request_timeout
        assert context.config.cache_ttl == config.cache_ttl
        assert context.config.use_cache == config.use_cache
        assert context.config.rate_limit_requests == config.rate_limit_requests
        assert context.config.rate_limit_period == config.rate_limit_period


@pytest.mark.asyncio
async def test_fetch_latest_threat_reports(ctx):
    """Test fetching latest threat reports."""
    result = await fetch_latest_threat_reports(ctx, limit=2)
    assert len(result) == 2
    assert result[0]["uuid"] == "test1"
    assert result[1]["uuid"] == "test2"
    ctx.request_context.lifespan_context.api_client.get_library_entries.assert_called_once_with(
        limit=2, order_by='created_at', order='desc'
    )


@pytest.mark.asyncio
async def test_fetch_threat_report_details(ctx):
    """Test fetching threat report details."""
    result = await fetch_threat_report_details(ctx, report_id="test1")
    assert result["uuid"] == "test1"
    assert result["title"] == "Test 1"
    assert result["content"] == "Test content"
    ctx.request_context.lifespan_context.api_client.get_library_entry.assert_called_once_with("test1")


@pytest.mark.asyncio
async def test_search_threat_reports(ctx):
    """Test searching threat reports."""
    result = await search_threat_reports(ctx, query="test", limit=2)
    assert len(result) == 2
    assert result[0]["uuid"] == "test1"
    assert result[1]["uuid"] == "test2"
    ctx.request_context.lifespan_context.api_client.search_library.assert_called_once_with("test", False, 2)


@pytest.mark.asyncio
async def test_get_library_info(ctx):
    """Test getting library information."""
    result = await get_library_info(ctx)
    assert result["name"] == "Test Library"
    assert result["version"] == "1.0.0"
    assert result["entries"] == 100
    ctx.request_context.lifespan_context.api_client.get_library_info.assert_called_once()


@pytest.mark.asyncio
async def test_get_library_version(ctx):
    """Test getting library version."""
    result = await get_library_version(ctx)
    assert result["version"] == "1.0.0"
    assert result["build_date"] == "2024-01-01"
    ctx.request_context.lifespan_context.api_client.get_library_version.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_threat_actors(ctx):
    """Test fetching threat actors."""
    result = await fetch_threat_actors(ctx)
    assert len(result) == 2
    assert result[0]["uuid"] == "ta1"
    assert result[1]["uuid"] == "ta2"
    ctx.request_context.lifespan_context.api_client.get_threat_actor_entries.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_threat_actor_details(ctx):
    """Test fetching threat actor details."""
    result = await fetch_threat_actor_details(ctx, actor_id="ta1")
    assert result["uuid"] == "ta1"
    assert result["name"] == "TA 1"
    assert result["description"] == "Test TA"
    ctx.request_context.lifespan_context.api_client.get_threat_actor_entry.assert_called_once_with("ta1")


@pytest.mark.asyncio
async def test_fetch_sources(ctx):
    """Test fetching sources."""
    result = await fetch_sources(ctx)
    assert len(result) == 2
    assert result[0]["uuid"] == "source1"
    assert result[1]["uuid"] == "source2"
    ctx.request_context.lifespan_context.api_client.get_source_entries.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_source_details(ctx):
    """Test fetching source details."""
    result = await fetch_source_details(ctx, source_id="source1")
    assert result["uuid"] == "source1"
    assert result["name"] == "Source 1"
    assert result["description"] == "Test source"
    ctx.request_context.lifespan_context.api_client.get_source_entry.assert_called_once_with("source1", False)


@pytest.mark.asyncio
async def test_clear_cache(ctx):
    """Test clearing cache."""
    result = await clear_cache(ctx, category="all")
    assert result == {"status": "success", "message": "Cache cleared"}
    # Note: We don't assert the cache clear call since it's handled internally
