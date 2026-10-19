"""Response cache for external travel APIs.

Redis when ``REDIS_URL`` is set (shared by every worker), otherwise a small
in-process TTL cache. A cache failure is logged and treated as a miss: the
cache must never be the reason a plan fails.
"""

import threading
import time
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_MEMORY_ENTRIES = 1024


class Cache(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...


class MemoryCache:
    """Thread safe TTL cache for a single process."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            entry = self._entries.get(key)

            if entry is None:
                return None

            expires_at, value = entry

            if expires_at < time.monotonic():
                del self._entries[key]
                return None

            return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        with self._lock:
            if len(self._entries) >= _MAX_MEMORY_ENTRIES:
                self._entries.pop(next(iter(self._entries)))

            self._entries[key] = (time.monotonic() + ttl_seconds, value)


class RedisCache:
    """Cache shared through Redis."""

    def __init__(self, url: str) -> None:
        import redis

        self._client = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> str | None:
        try:
            return self._client.get(key)
        except Exception as error:  # noqa: BLE001 - a broken cache is a miss
            logger.warning("Redis get failed: %s", error)
            return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self._client.set(key, value, ex=ttl_seconds)
        except Exception as error:  # noqa: BLE001
            logger.warning("Redis set failed: %s", error)


@lru_cache(maxsize=1)
def get_cache() -> Cache:
    """Return the process-wide cache."""

    settings = get_settings()

    if settings.redis_url:
        logger.info("Caching travel API responses in Redis")
        return RedisCache(settings.redis_url)

    return MemoryCache()
