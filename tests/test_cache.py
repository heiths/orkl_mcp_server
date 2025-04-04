"""Tests for the caching utility."""

import time

from orkl_mcp.utils.cache import Cache, CacheEntry


def test_cache_entry():
    """Test that a cache entry can be created with a value and expiration time."""
    entry = CacheEntry(value="test", expires_at=time.time() + 60)
    assert entry.value == "test"
    assert entry.expires_at > time.time()


def test_cache_set_get():
    """Test setting and getting items from the cache."""
    cache = Cache()
    
    # Set an item
    cache.set("key1", "value1", 60)
    
    # Get the item
    assert cache.get("key1") == "value1"
    
    # Get a non-existent item
    assert cache.get("nonexistent") is None


def test_cache_expiration():
    """Test that expired items are removed from the cache."""
    cache = Cache()
    
    # Set an item with a very short TTL
    cache.set("short_lived", "value", 0.1)
    
    # Verify it exists initially
    assert cache.get("short_lived") == "value"
    
    # Wait for it to expire
    time.sleep(0.2)
    
    # Verify it's gone
    assert cache.get("short_lived") is None


def test_cache_lru_eviction():
    """Test that least recently used items are evicted when the cache is full."""
    # Create a cache with a max size of 2
    cache = Cache(max_size=2)
    
    # Set two items
    cache.set("key1", "value1", 60)
    cache.set("key2", "value2", 60)
    
    # Both should exist
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"
    
    # Add a third item, which should evict key1 (least recently used)
    cache.set("key3", "value3", 60)
    
    # key1 should be gone, key2 and key3 should exist
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"
    
    # Access key2 to update its LRU status
    assert cache.get("key2") == "value2"
    
    # Add a fourth item, which should evict key3 (now the least recently used)
    cache.set("key4", "value4", 60)
    
    # key3 should be gone, key2 and key4 should exist
    assert cache.get("key3") is None
    assert cache.get("key2") == "value2"
    assert cache.get("key4") == "value4"


def test_cache_delete():
    """Test explicitly deleting items from the cache."""
    cache = Cache()
    
    # Set two items
    cache.set("key1", "value1", 60)
    cache.set("key2", "value2", 60)
    
    # Both should exist
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"
    
    # Delete one
    cache.delete("key1")
    
    # key1 should be gone, key2 should still exist
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"
    
    # Delete a non-existent key (should not raise an error)
    cache.delete("nonexistent")


def test_cache_clear():
    """Test clearing the entire cache."""
    cache = Cache()
    
    # Set multiple items
    cache.set("key1", "value1", 60)
    cache.set("key2", "value2", 60)
    cache.set("key3", "value3", 60)
    
    # Clear the cache
    cache.clear()
    
    # All items should be gone
    assert cache.get("key1") is None
    assert cache.get("key2") is None
    assert cache.get("key3") is None


def test_cache_clear_by_prefix():
    """Test clearing items with a specific prefix."""
    cache = Cache()
    
    # Set items with different prefixes
    cache.set("a:item1", "value1", 60)
    cache.set("a:item2", "value2", 60)
    cache.set("b:item1", "value3", 60)
    cache.set("c:item1", "value4", 60)
    
    # Clear items with prefix "a:"
    cache.clear_by_prefix("a:")
    
    # Items with prefix "a:" should be gone, others should remain
    assert cache.get("a:item1") is None
    assert cache.get("a:item2") is None
    assert cache.get("b:item1") == "value3"
    assert cache.get("c:item1") == "value4"
