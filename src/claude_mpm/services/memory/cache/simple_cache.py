#!/usr/bin/env python3
"""
Simple In-Memory Cache Service Implementation
============================================

Provides a thread-safe in-memory cache implementation with TTL support,
file modification tracking, and cache invalidation capabilities.

Features:
- TTL-based expiration
- File modification time tracking for automatic invalidation
- Pattern-based cache invalidation
- Thread-safe operations
- Performance metrics tracking
"""

import fnmatch
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from claude_mpm.core.interfaces import ICacheService

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata."""

    key: str
    value: Any
    created_at: float
    ttl: Optional[float] = None
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    tracked_files: Set[Path] = field(default_factory=set)
    file_mtimes: Dict[str, float] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def is_stale(self) -> bool:
        """Check if tracked files have been modified."""
        for file_path in self.tracked_files:
            if file_path.exists():
                current_mtime = file_path.stat().st_mtime
                stored_mtime = self.file_mtimes.get(str(file_path), 0)
                if current_mtime > stored_mtime:
                    return True
            else:
                # File was deleted, cache is stale
                return True
        return False


class SimpleCacheService(ICacheService):
    """
    Thread-safe in-memory cache service with TTL and file tracking support.

    This implementation provides:
    - Automatic expiration based on TTL
    - File modification tracking for cache invalidation
    - Pattern-based invalidation
    - Thread safety with read-write locks
    - Performance metrics
    """

    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        """
        Initialize the cache service.

        Args:
            default_ttl: Default time-to-live in seconds (default: 1 hour)
            max_size: Maximum number of cache entries (default: 1000)
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.lock = threading.RLock()

        # Performance metrics
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "invalidations": 0,
            "evictions": 0,
            "stale_hits": 0,
        }

        # Start background cleanup thread
        self.cleanup_interval = 60  # seconds
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

        logger.info(
            f"SimpleCacheService initialized with TTL={default_ttl}s, max_size={max_size}"
        )

    def get(self, key: str) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired/stale
        """
        with self.lock:
            entry = self.cache.get(key)

            if entry is None:
                self.metrics["misses"] += 1
                return None

            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                self.metrics["misses"] += 1
                logger.debug(f"Cache miss (expired): {key}")
                return None

            # Check if files have been modified
            if entry.is_stale():
                del self.cache[key]
                self.metrics["stale_hits"] += 1
                self.metrics["misses"] += 1
                logger.debug(f"Cache miss (stale): {key}")
                return None

            # Update access metadata
            entry.access_count += 1
            entry.last_accessed = time.time()

            self.metrics["hits"] += 1
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tracked_files: Optional[List[Path]] = None,
    ) -> None:
        """
        Set value in cache with optional TTL and file tracking.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
            tracked_files: List of files to track for modification
        """
        with self.lock:
            # Evict entries if at max size
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()

            ttl = ttl if ttl is not None else self.default_ttl
            expires_at = time.time() + ttl if ttl > 0 else None

            # Track file modification times
            file_mtimes = {}
            tracked_file_set = set()

            if tracked_files:
                for file_path in tracked_files:
                    if isinstance(file_path, str):
                        file_path = Path(file_path)
                    if file_path.exists():
                        tracked_file_set.add(file_path)
                        file_mtimes[str(file_path)] = file_path.stat().st_mtime

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl,
                expires_at=expires_at,
                tracked_files=tracked_file_set,
                file_mtimes=file_mtimes,
            )

            self.cache[key] = entry
            self.metrics["sets"] += 1

            logger.debug(
                f"Cache set: {key} (TTL={ttl}s, tracking {len(tracked_file_set)} files)"
            )

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.metrics["deletes"] += 1
                logger.debug(f"Cache delete: {key}")
                return True
            return False

    def invalidate(self, pattern: str) -> int:
        """
        Invalidate keys matching pattern.

        Args:
            pattern: Unix-style pattern (e.g., "agent_*")

        Returns:
            Number of keys invalidated
        """
        with self.lock:
            keys_to_delete = []

            for key in self.cache:
                if fnmatch.fnmatch(key, pattern):
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.cache[key]

            count = len(keys_to_delete)
            if count > 0:
                self.metrics["invalidations"] += count
                logger.info(
                    f"Invalidated {count} cache entries matching pattern: {pattern}"
                )

            return count

    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            self.metrics["invalidations"] += count
            logger.info(f"Cleared {count} cache entries")

    def get_cache_metrics(self) -> Dict[str, Any]:
        """
        Get cache performance metrics.

        Returns:
            Dictionary containing cache metrics
        """
        with self.lock:
            total_requests = self.metrics["hits"] + self.metrics["misses"]
            hit_rate = (
                (self.metrics["hits"] / total_requests * 100)
                if total_requests > 0
                else 0
            )

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.metrics["hits"],
                "misses": self.metrics["misses"],
                "hit_rate": f"{hit_rate:.2f}%",
                "sets": self.metrics["sets"],
                "deletes": self.metrics["deletes"],
                "invalidations": self.metrics["invalidations"],
                "evictions": self.metrics["evictions"],
                "stale_hits": self.metrics["stale_hits"],
                "total_requests": total_requests,
            }

    def track_file(self, key: str, file_path: Path) -> None:
        """
        Add a file to track for an existing cache entry.

        Args:
            key: Cache key
            file_path: File path to track
        """
        with self.lock:
            entry = self.cache.get(key)
            if entry and file_path.exists():
                entry.tracked_files.add(file_path)
                entry.file_mtimes[str(file_path)] = file_path.stat().st_mtime
                logger.debug(f"Added file tracking for {key}: {file_path}")

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.cache:
            return

        # Find LRU entry
        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k].last_accessed)

        del self.cache[lru_key]
        self.metrics["evictions"] += 1
        logger.debug(f"Evicted LRU entry: {lru_key}")

    def _cleanup_loop(self) -> None:
        """Background thread to clean up expired entries."""
        while True:
            time.sleep(self.cleanup_interval)
            self._cleanup_expired()

    def _cleanup_expired(self) -> None:
        """Remove expired and stale entries."""
        with self.lock:
            keys_to_delete = []

            for key, entry in self.cache.items():
                if entry.is_expired() or entry.is_stale():
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.cache[key]

            if keys_to_delete:
                logger.debug(f"Cleaned up {len(keys_to_delete)} expired/stale entries")
