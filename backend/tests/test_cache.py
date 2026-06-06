"""Tests for the cache layer."""

from backend.cache import CacheManager, MemoryCacheBackend


def test_memory_cache_roundtrip():
    backend = MemoryCacheBackend()
    backend.set("key", {"value": 1}, ttl_seconds=60)
    assert backend.get("key") == {"value": 1}
    backend.delete("key")
    assert backend.get("key") is None


def test_cache_manager_get_or_set():
    manager = CacheManager()
    manager.backend = MemoryCacheBackend()
    calls = {"count": 0}

    def compute():
        calls["count"] += 1
        return {"computed": True}

    first = manager.get_or_set("compute:key", compute, ttl_seconds=60)
    second = manager.get_or_set("compute:key", compute, ttl_seconds=60)
    assert first == second == {"computed": True}
    assert calls["count"] == 1
