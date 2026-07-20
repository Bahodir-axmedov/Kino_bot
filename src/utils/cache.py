"""Tiny in-process TTL cache.

This is intentionally dependency-free (no ``cachetools``/Redis requirement)
so the "tezlik" requirements (in-memory caching for hot lookups such as
movie-by-code and force-subscribe membership) can be satisfied without
adding new third-party packages that cannot be pip-installed/verified in
this sandbox. If the bot is later scaled to multiple processes, this should
be swapped for the already-configured ``REDIS_URL`` backend -- the call
sites (``TTLCache.get``/``set``/``invalidate``) are the only integration
seam that would need to change.

The methods are intentionally **synchronous**. The bot runs a single asyncio
event loop, and each operation here is a handful of dict operations with no
``await`` inside, so it cannot be interrupted mid-update -- that makes it
coroutine-safe without a lock. (An earlier async version was a latent bug
magnet: every caller used it *without* ``await``, so ``get`` returned a
coroutine object instead of the cached value.)
"""

from __future__ import annotations

import time
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """A minimal, coroutine-safe cache with per-entry time-to-live expiry.

    Uses a single ``asyncio.Lock`` for mutation safety. Reads are O(1) dict
    lookups; writes are O(1). A lazy sweep (on write) bounds unbounded growth
    without needing a background task.
    """

    def __init__(self, *, ttl_seconds: float, max_size: int = 5000) -> None:
        """Configure the cache's expiry window and a soft maximum size."""
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._store: dict[K, tuple[float, V]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: K) -> V | None:
        """Return the cached value for ``key``, or ``None`` if missing/expired."""
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            self.misses += 1
            return None
        self.hits += 1
        return value

    def set(self, key: K, value: V) -> None:
        """Store ``value`` under ``key`` with the configured TTL."""
        if len(self._store) >= self._max_size:
            self._sweep_expired_locked()
        if len(self._store) >= self._max_size:
            # Still full after sweeping expired entries: drop the oldest
            # arbitrary entry rather than growing unbounded (defends
            # against unbounded memory growth / "memory leak").
            oldest_key = next(iter(self._store), None)
            if oldest_key is not None:
                self._store.pop(oldest_key, None)
        self._store[key] = (time.monotonic() + self._ttl, value)

    def invalidate(self, key: K) -> None:
        """Remove a single key from the cache, if present."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Remove every entry from the cache."""
        self._store.clear()

    def _sweep_expired_locked(self) -> None:
        """Drop expired entries."""
        now = time.monotonic()
        expired = [key for key, (expires_at, _value) in self._store.items() if expires_at < now]
        for key in expired:
            self._store.pop(key, None)

    def stats(self) -> dict[str, int | float]:
        """Return simple hit/miss/size counters for the dashboard."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total else 0.0
        return {
            "size": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": round(hit_rate * 100, 2),
        }
