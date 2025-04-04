"""ORKL API client for interacting with the threat intelligence API."""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, TypeVar, cast

import httpx
from pydantic import BaseModel

from orkl_mcp.config import OrklConfig, load_config
from orkl_mcp.utils.cache import Cache
from orkl_mcp.exceptions import OrklAPIError, OrklRateLimitError

T = TypeVar("T")


class RateLimiter:
    """Rate limiter to prevent exceeding API limits."""

    def __init__(self, max_requests: int, period: int) -> None:
        """Initialize a new rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the period.
            period: Time period in seconds.
        """
        self.max_requests = max_requests
        self.period = period
        self.request_times: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a request.

        This method blocks until a request can be made without exceeding the rate limit.
        """
        async with self._lock:
            now = time.time()

            # Remove timestamps older than the period
            self.request_times = [t for t in self.request_times if now - t < self.period]

            if len(self.request_times) >= self.max_requests:
                # We need to wait until we can make another request
                oldest = min(self.request_times)
                sleep_time = self.period - (now - oldest)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            # Record this request
            self.request_times.append(time.time())


class ApiError(Exception):
    """Exception raised for API errors."""

    def __init__(
            self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize a new API error.

        Args:
            message: Error message.
            status_code: HTTP status code.
            response: Raw API response.
        """
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class OrklApiClient:
    """Client for interacting with the ORKL Threat Intelligence API."""

    def __init__(self, config: OrklConfig) -> None:
        """Initialize the API client.

        Args:
            config: ORKL configuration.
        """
        self.config = config
        self.cache = Cache()
        self.client = httpx.AsyncClient()
        self.rate_limiter = RateLimiter(
            max_requests=config.rate_limit_requests,
            period=config.rate_limit_period,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the ORKL API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to httpx

        Returns:
            API response as a dictionary
        """
        url = f"{self.config.api_base_url}/{endpoint.lstrip('/')}"

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "orkl-mcp-server/0.1.0",
        }

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        # Handle caching
        cache_key = kwargs.pop("cache_key", None)
        use_cache = kwargs.pop("use_cache", self.config.use_cache)

        if cache_key and use_cache:
            cached_response = self.cache.get(cache_key)
            if cached_response is not None:
                return cached_response

        try:
            response = await self.client.request(
                method,
                url,
                headers=headers,
                timeout=self.config.request_timeout,
                **kwargs
            )

            response.raise_for_status()
            result = response.json()

            if cache_key and use_cache:
                self.cache.set(cache_key, result, self.config.cache_ttl)

            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", "30"))
                raise OrklRateLimitError(
                    "Rate limit exceeded",
                    retry_after=retry_after
                ) from e
            raise OrklAPIError(
                f"API error: {e.response.status_code}",
                status_code=e.response.status_code,
                response=e.response.json() if e.response.content else None
            ) from e
        except httpx.RequestError as e:
            raise OrklAPIError(f"Request error: {str(e)}") from e

    async def get_library_entries(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order_by: str = "created_at",
            order: str = "desc",
            use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get library entries.

        Args:
            limit: Maximum number of entries to return.
            offset: Offset for pagination.
            order_by: Field to order by.
            order: Order direction ('asc' or 'desc').
            use_cache: Whether to use cached results.

        Returns:
            API response with library entries.
        """
        params: Dict[str, Any] = {
            "order_by": order_by,
            "order": order,
        }
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        # Generate a cache key based on the parameters
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cache_key = f"library_entries:{param_str}"

        return await self._make_request(
            "GET", "/library/entries", params=params, cache_key=cache_key, use_cache=use_cache
        )

    async def get_library_entry(self, uuid: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get a library entry by UUID.

        Args:
            uuid: Entry UUID.
            use_cache: Whether to use cached results.

        Returns:
            API response with the library entry.
        """
        cache_key = f"library_entry:{uuid}"
        return await self._make_request(
            "GET", f"/library/entry/{uuid}", cache_key=cache_key, use_cache=use_cache
        )

    async def get_library_entry_by_sha1(self, sha1_hash: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get a library entry by SHA1 hash.

        Args:
            sha1_hash: SHA1 hash.
            use_cache: Whether to use cached results.

        Returns:
            API response with the library entry.
        """
        cache_key = f"library_entry_sha1:{sha1_hash}"
        return await self._make_request(
            "GET", f"/library/entry/sha1/{sha1_hash}", cache_key=cache_key, use_cache=use_cache
        )

    async def search_library(
            self, query: str, full: bool = False, limit: int = 1000, use_cache: bool = True
    ) -> Dict[str, Any]:
        """Search the library.

        Args:
            query: Search query.
            full: Whether to return full entries.
            limit: Maximum number of entries to return.
            use_cache: Whether to use cached results.

        Returns:
            API response with search results.
        """
        params = {
            "query": query,
            "full": str(full).lower(),
            "limit": limit,
        }

        # For search queries, include a timestamp in the cache key to ensure
        # it expires after the configured TTL
        cache_time = int(time.time() / self.config.cache_ttl)
        cache_key = f"search:{query}:{full}:{limit}:{cache_time}"

        return await self._make_request(
            "GET", "/library/search", params=params, cache_key=cache_key, use_cache=use_cache
        )

    async def get_library_info(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get library information.

        Args:
            use_cache: Whether to use cached results.

        Returns:
            API response with library information.
        """
        # Include a timestamp in the cache key to ensure it expires after the configured TTL
        cache_time = int(time.time() / self.config.cache_ttl)
        cache_key = f"library_info:{cache_time}"

        return await self._make_request(
            "GET", "/library/info", cache_key=cache_key, use_cache=use_cache
        )

    async def get_library_version(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get library version.

        Args:
            use_cache: Whether to use cached results.

        Returns:
            API response with library version.
        """
        # Include a timestamp in the cache key to ensure it expires after the configured TTL
        cache_time = int(time.time() / self.config.cache_ttl)
        cache_key = f"library_version:{cache_time}"

        return await self._make_request(
            "GET", "/library/version", cache_key=cache_key, use_cache=use_cache
        )

    async def get_library_version_entries(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            order: str = "desc",
            use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Get library version entries.

        Args:
            limit: Maximum number of entries to return.
            offset: Offset for pagination.
            order: Order direction ('asc' or 'desc').
            use_cache: Whether to use cached results.

        Returns:
            API response with library version entries.
        """
        params: Dict[str, Any] = {
            "order": order,
        }
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        # Generate a cache key based on the parameters
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cache_key = f"library_version_entries:{param_str}"

        return await self._make_request(
            "GET", "/library/version/entries", params=params, cache_key=cache_key, use_cache=use_cache
        )

    async def get_library_work_entries(
            self, limit: Optional[int] = None, use_cache: bool = True
    ) -> Dict[str, Any]:
        """Get library work entries.

        Args:
            limit: Maximum number of entries to return.
            use_cache: Whether to use cached results.

        Returns:
            API response with library work entries.
        """
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit

        # Generate a cache key based on the parameters
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cache_key = f"library_work_entries:{param_str}"

        return await self._make_request(
            "GET", "/library/work/entries", params=params, cache_key=cache_key, use_cache=use_cache
        )

    async def get_source_entries(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get source entries.

        Args:
            use_cache: Whether to use cached results.

        Returns:
            API response with source entries.
        """
        cache_key = "source_entries"
        return await self._make_request(
            "GET", "/source/entries", cache_key=cache_key, use_cache=use_cache
        )

    async def get_source_entry(
            self, uuid: str, full: bool = False, use_cache: bool = True
    ) -> Dict[str, Any]:
        """Get a source entry by UUID.

        Args:
            uuid: Entry UUID.
            full: Whether to return the full entry including reports.
            use_cache: Whether to use cached results.

        Returns:
            API response with the source entry.
        """
        params = {
            "full": str(full).lower(),
        }
        cache_key = f"source_entry:{uuid}:{full}"
        return await self._make_request(
            "GET", f"/source/entry/{uuid}", params=params, cache_key=cache_key, use_cache=use_cache
        )

    async def get_threat_actor_entries(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get threat actor entries.

        Args:
            use_cache: Whether to use cached results.

        Returns:
            API response with threat actor entries.
        """
        cache_key = "ta_entries"
        return await self._make_request(
            "GET", "/ta/entries", cache_key=cache_key, use_cache=use_cache
        )

    async def get_threat_actor_entry(self, uuid: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get a threat actor entry by UUID.

        Args:
            uuid: Entry UUID.
            use_cache: Whether to use cached results.

        Returns:
            API response with the threat actor entry.
        """
        cache_key = f"ta_entry:{uuid}"
        return await self._make_request(
            "GET", f"/ta/entry/{uuid}", cache_key=cache_key, use_cache=use_cache
        )

    def clear_cache(self, category: Optional[str] = None) -> None:
        """Clear the cache.

        Args:
            category: Optional category to clear. If None, the entire cache is cleared.
                Valid categories: 'threat_reports', 'threat_actors', 'sources', 'all'.
        """
        if category is None or category == "all":
            self.cache.clear()
        elif category == "threat_reports":
            self.cache.clear_by_prefix("library_")
            self.cache.clear_by_prefix("search:")
        elif category == "threat_actors":
            self.cache.clear_by_prefix("ta_")
        elif category == "sources":
            self.cache.clear_by_prefix("source_")
        else:
            raise ValueError(
                "Invalid cache category. Valid values: 'threat_reports', 'threat_actors', 'sources', 'all'"
            )
