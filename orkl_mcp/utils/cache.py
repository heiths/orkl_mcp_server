"""Caching utilities for the ORKL MCP server."""

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A cache entry with a value and expiration time."""

    value: T
    expires_at: float


class Cache:
    """A simple in-memory cache with expiration."""

    def __init__(self, max_size: int = 1000) -> None:
        """Initialize a new cache.

        Args:
            max_size: Maximum number of items to store in the cache.
        """
        self._cache: OrderedDict[str, CacheEntry[Any]] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value, or None if the key is not in the cache or has expired.
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if entry.expires_at < time.time():
            # Entry has expired, remove it
            del self._cache[key]
            return None

        # Move the accessed key to the end (most recently used)
        self._cache.move_to_end(key)
        return entry.value

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time to live in seconds.
        """
        # Enforce cache size limit (LRU eviction)
        if len(self._cache) >= self._max_size and key not in self._cache:
            # Remove the oldest item (first item in the OrderedDict)
            self._cache.popitem(last=False)

        expires_at = time.time() + ttl
        self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        """Delete a key from the cache.

        Args:
            key: The cache key to delete.
        """
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()

    def clear_by_prefix(self, prefix: str) -> None:
        """Clear all cache entries with keys starting with the given prefix.

        Args:
            prefix: The key prefix to match.
        """
        keys_to_delete = [key for key in self._cache.keys() if key.startswith(prefix)]
        for key in keys_to_delete:
            del self._cache[key]
