"""
cache.py
--------
Caching layer with Redis fallback to in-memory cache.
Improves performance for frequently accessed data (memories, sessions).

Usage:
    from backend.cache import cache
    
    # Set with TTL
    cache.set("session:sess-001", session_data, ttl_seconds=3600)
    
    # Get
    session = cache.get("session:sess-001")
    
    # Delete
    cache.delete("session:sess-001")
    
    # Clear all
    cache.clear()
"""

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheBackend:
    """Abstract cache interface."""

    def get(self, key: str) -> Any:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def backend_name(self) -> str:
        raise NotImplementedError


class MemoryCacheBackend(CacheBackend):
    """In-memory cache (fallback when Redis unavailable)."""

    def __init__(self):
        self.store: dict[str, tuple[Any, Optional[float]]] = {}

    def get(self, key: str) -> Any:
        """Get value from memory cache."""
        if key not in self.store:
            return None

        value, expiry = self.store[key]
        if expiry is not None:
            import time

            if time.time() > expiry:
                del self.store[key]
                return None

        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set value in memory cache with TTL."""
        import time

        expiry = time.time() + ttl_seconds if ttl_seconds > 0 else None
        self.store[key] = (value, expiry)

    def delete(self, key: str) -> None:
        """Delete key from memory cache."""
        self.store.pop(key, None)

    def clear(self) -> None:
        """Clear all entries from memory cache."""
        self.store.clear()

    def backend_name(self) -> str:
        return "memory"


class RedisCacheBackend(CacheBackend):
    """Redis cache backend for distributed caching."""

    def __init__(self, redis_url: str | None = None):
        """Initialize Redis client. redis_url = redis://host:port/db"""
        import redis

        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=5)
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Falling back to memory cache.")
            self.client = None

    def get(self, key: str) -> Any:
        """Get value from Redis cache."""
        if not self.client:
            return None

        try:
            value = self.client.get(key)
            if value is None:
                return None
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # If not JSON, return as string
                return value
        except Exception as e:
            logger.warning(f"Redis get failed for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set value in Redis cache with TTL."""
        if not self.client:
            return

        try:
            # Serialize to JSON
            serialized = json.dumps(value, default=str)
            if ttl_seconds > 0:
                self.client.setex(key, ttl_seconds, serialized)
            else:
                self.client.set(key, serialized)
        except Exception as e:
            logger.warning(f"Redis set failed for key {key}: {e}")

    def delete(self, key: str) -> None:
        """Delete key from Redis cache."""
        if not self.client:
            return

        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed for key {key}: {e}")

    def clear(self) -> None:
        """Clear all entries from Redis cache."""
        if not self.client:
            return

        try:
            self.client.flushdb()
        except Exception as e:
            logger.warning(f"Redis flushdb failed: {e}")

    def backend_name(self) -> str:
        return "redis" if self.client else "memory (redis unavailable)"


class CacheManager:
    """Facade for cache operations with automatic backend selection."""

    def __init__(self):
        """Initialize with Redis or memory backend."""
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            self.backend = RedisCacheBackend(redis_url)
            # If Redis connection failed, it falls back to memory internally
            if not isinstance(self.backend, RedisCacheBackend) or not self.backend.client:
                logger.info("Using memory cache fallback")
                self.backend = MemoryCacheBackend()
        else:
            logger.info("No REDIS_URL set, using memory cache")
            self.backend = MemoryCacheBackend()

    def get(self, key: str) -> Any:
        """Get cached value by key."""
        return self.backend.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set cached value with TTL (seconds)."""
        self.backend.set(key, value, ttl_seconds)

    def delete(self, key: str) -> None:
        """Delete cached value."""
        self.backend.delete(key)

    def clear(self) -> None:
        """Clear all cache entries."""
        self.backend.clear()

    def backend_name(self) -> str:
        """Get current backend name."""
        return self.backend.backend_name()

    # Convenience methods for common patterns
    def get_or_set(self, key: str, compute_fn, ttl_seconds: int = 3600) -> Any:
        """Get from cache or compute and cache if missing."""
        value = self.get(key)
        if value is not None:
            return value

        value = compute_fn()
        self.set(key, value, ttl_seconds)
        return value

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern (Redis only, memory ignores)."""
        if isinstance(self.backend, RedisCacheBackend) and self.backend.client:
            try:
                keys = self.backend.client.keys(pattern)
                if keys:
                    self.backend.client.delete(*keys)
                    return len(keys)
            except Exception as e:
                logger.warning(f"Failed to invalidate pattern {pattern}: {e}")
        return 0


# Global cache instance
cache = CacheManager()
