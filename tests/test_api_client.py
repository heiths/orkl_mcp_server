"""Tests for the ORKL API client."""

import json
import time
from typing import Any, Dict, List, cast, Optional
from unittest import mock

import httpx
import pytest
from anyio import sleep

from orkl_mcp.api_client import ApiError, OrklApiClient, RateLimiter
from orkl_mcp.config import OrklConfig
from orkl_mcp.exceptions import OrklAPIError, OrklRateLimitError


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        text: str = "",
        raise_for_status: bool = False,
    ):
        """Initialize a mock response.

        Args:
            status_code: HTTP status code.
            json_data: JSON data to return.
            text: Response text.
            raise_for_status: Whether to raise an exception when raise_for_status() is called.
        """
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text
        self._raise_for_status = raise_for_status
        self.content = b""  # Add content attribute
        self.headers = {}  # Add headers attribute

    def json(self) -> Dict[str, Any]:
        """Return JSON data."""
        return self._json_data

    def raise_for_status(self) -> None:
        """Raise an exception if raise_for_status is True."""
        if self._raise_for_status:
            raise httpx.HTTPStatusError(
                "HTTP error",
                request=httpx.Request("GET", "https://example.com"),
                response=cast(httpx.Response, self),
            )


@pytest.fixture
def config():
    """Create a test configuration."""
    return OrklConfig(
        api_base_url="https://test.example.com/api",
        request_timeout=5,
        cache_ttl=10,
        use_cache=True,
        rate_limit_requests=10,
        rate_limit_period=1,
    )


@pytest.fixture
def mock_client():
    """Create a mock httpx.AsyncClient."""
    mock_client = mock.AsyncMock()
    mock_client.request = mock.AsyncMock()
    mock_client.aclose = mock.AsyncMock()
    return mock_client


@pytest.fixture
def client(config, mock_client):
    """Create a test client with mocked httpx.AsyncClient."""
    client = OrklApiClient(config)
    client.client = mock_client
    return client


@pytest.fixture
def mock_successful_response():
    """Create a mock successful API response."""
    return MockResponse(
        json_data={"status": "success", "message": "OK", "data": {"test": "data"}}
    )


@pytest.fixture
def mock_error_response():
    """Create a mock error API response."""
    return MockResponse(
        status_code=400,
        json_data={"status": "error", "message": "Bad request", "data": None},
        raise_for_status=True,
    )


@pytest.mark.anyio
async def test_rate_limiter():
    """Test that the rate limiter correctly limits request rate."""
    # Create a rate limiter with 3 requests per 0.5 seconds
    limiter = RateLimiter(max_requests=3, period=1)
    
    # Make 3 requests (should not block)
    start_time = time.time()
    for _ in range(3):
        await limiter.acquire()
    
    # This should be quick
    assert time.time() - start_time < 0.1
    
    # Make another request (should block until the period expires)
    await limiter.acquire()
    
    # This should have taken at least 0.5 seconds
    assert time.time() - start_time >= 0.5


@pytest.mark.anyio
async def test_request_success(client, mock_client, mock_successful_response):
    """Test successful request handling."""
    mock_client.request.return_value = mock_successful_response
    result = await client._make_request("GET", "/test")
    assert result == mock_successful_response._json_data
    mock_client.request.assert_called_once()


@pytest.mark.anyio
async def test_request_http_error(client, mock_client):
    """Test handling of HTTP errors."""
    error_response = MockResponse(
        status_code=404,
        json_data={"status": "error", "message": "Not found"},
        raise_for_status=True
    )
    mock_client.request.return_value = error_response
    
    with pytest.raises(OrklAPIError) as exc_info:
        await client._make_request("GET", "/test")
    
    assert "API error: 404" in str(exc_info.value)
    mock_client.request.assert_called_once()


@pytest.mark.anyio
async def test_request_invalid_method(client):
    """Test handling of invalid HTTP methods."""
    with mock.patch.object(
        client.client, "request", side_effect=httpx.RequestError("Unsupported HTTP method")
    ):
        with pytest.raises(OrklAPIError) as exc_info:
            await client._make_request("POST", "/test")
        assert str(exc_info.value) == "Request error: Unsupported HTTP method"


@pytest.mark.anyio
async def test_request_invalid_json(client, mock_client):
    """Test handling of invalid JSON responses."""
    mock_response = MockResponse()
    mock_response.json = mock.Mock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
    mock_client.request.return_value = mock_response

    with pytest.raises(json.JSONDecodeError) as exc_info:
        await client._make_request("GET", "/test")
    assert str(exc_info.value) == "Invalid JSON: line 1 column 1 (char 0)"


@pytest.mark.anyio
async def test_request_api_error(client):
    """Test handling of API errors."""
    response = MockResponse(
        json_data={"status": "error", "message": "API error", "data": None},
        status_code=500
    )
    response.raise_for_status = mock.Mock(side_effect=httpx.HTTPStatusError(
        "API error",
        request=mock.Mock(),
        response=mock.Mock(
            status_code=500,
            content=b'{"error": "Internal server error"}',
            json=lambda: {"error": "Internal server error"},
        ),
    ))

    with mock.patch.object(client.client, "request", return_value=response):
        with pytest.raises(OrklAPIError) as exc_info:
            await client._make_request("GET", "/test")
        assert exc_info.value.status_code == 500


@pytest.mark.anyio
async def test_request_network_error(client, mock_client):
    """Test handling of network errors."""
    mock_client.request.side_effect = httpx.RequestError("Network error")
    
    with pytest.raises(OrklAPIError) as exc_info:
        await client._make_request("GET", "/test")
    
    assert "Request error: Network error" in str(exc_info.value)
    mock_client.request.assert_called_once()


@pytest.mark.anyio
async def test_request_caching(client, mock_client, mock_successful_response):
    """Test that responses are correctly cached."""
    mock_client.request.return_value = mock_successful_response
    
    # First request should hit the API
    result1 = await client._make_request("GET", "/test", cache_key="test_cache")
    assert result1 == mock_successful_response._json_data
    mock_client.request.assert_called_once()
    
    # Second request should use cached response
    mock_client.request.reset_mock()
    result2 = await client._make_request("GET", "/test", cache_key="test_cache")
    assert result2 == mock_successful_response._json_data
    mock_client.request.assert_not_called()


@pytest.mark.anyio
async def test_get_library_entries(client, mock_client, mock_successful_response):
    """Test the get_library_entries method."""
    mock_client.request.return_value = mock_successful_response

    result = await client.get_library_entries(limit=10, order_by="updated_at")
    assert result == mock_successful_response._json_data

    mock_client.request.assert_called_once_with(
        "GET",
        "https://test.example.com/api/library/entries",
        headers=mock.ANY,
        params={"order_by": "updated_at", "order": "desc", "limit": 10},
        timeout=mock.ANY
    )


@pytest.mark.anyio
async def test_get_library_entry(client, mock_client, mock_successful_response):
    """Test the get_library_entry method."""
    mock_client.request.return_value = mock_successful_response
    
    result = await client.get_library_entry("test-uuid")
    assert result == mock_successful_response._json_data
    
    mock_client.request.assert_called_once_with(
        "GET",
        "https://test.example.com/api/library/entry/test-uuid",
        headers=mock.ANY,
        timeout=mock.ANY
    )


def test_clear_cache(client):
    """Test the clear_cache method."""
    # Set up some cache entries
    client.cache.set("library_entry:1", "value1", 60)
    client.cache.set("ta_entry:1", "value2", 60)
    client.cache.set("source_entry:1", "value3", 60)
    
    # Clear threat reports cache
    client.clear_cache("threat_reports")
    assert client.cache.get("library_entry:1") is None
    assert client.cache.get("ta_entry:1") == "value2"
    assert client.cache.get("source_entry:1") == "value3"
    
    # Reset cache
    client.cache.set("library_entry:1", "value1", 60)
    
    # Clear threat actors cache
    client.clear_cache("threat_actors")
    assert client.cache.get("library_entry:1") == "value1"
    assert client.cache.get("ta_entry:1") is None
    assert client.cache.get("source_entry:1") == "value3"
    
    # Clear all cache
    client.clear_cache("all")
    assert client.cache.get("library_entry:1") is None
    assert client.cache.get("ta_entry:1") is None
    assert client.cache.get("source_entry:1") is None
    
    # Test invalid category
    with pytest.raises(ValueError):
        client.clear_cache("invalid")


@pytest.mark.anyio
async def test_get_library_info(client, mock_client):
    """Test getting library information."""
    mock_response = {
        "status": "success",
        "data": {
            "name": "Test Library",
            "version": "1.0.0",
            "entries": 100,
        },
    }
    
    mock_response_obj = MockResponse(json_data=mock_response)
    mock_client.request.return_value = mock_response_obj
    
    result = await client.get_library_info()
    assert result == mock_response
    
    mock_client.request.assert_called_once_with(
        "GET",
        "https://test.example.com/api/library/info",
        headers=mock.ANY,
        timeout=mock.ANY
    )


@pytest.mark.asyncio
async def test_rate_limit_error(client):
    """Test handling of rate limit errors."""
    mock_response = mock.Mock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "30"}
    mock_response.json.return_value = {"error": "Rate limit exceeded"}
    mock_response.content = b'{"error": "Rate limit exceeded"}'

    with mock.patch.object(
        client.client,
        "request",
        side_effect=httpx.HTTPStatusError(
            "Rate limit exceeded",
            request=mock.Mock(),
            response=mock_response,
        ),
    ):
        with pytest.raises(OrklRateLimitError) as exc_info:
            await client._make_request("GET", "/test")
        assert exc_info.value.retry_after == 30


@pytest.mark.asyncio
async def test_request_error(client):
    """Test handling of request errors."""
    with mock.patch.object(
        client.client,
        "request",
        side_effect=httpx.RequestError("Connection error"),
    ):
        with pytest.raises(OrklAPIError) as exc_info:
            await client._make_request("GET", "/test")
        assert str(exc_info.value) == "Request error: Connection error"
