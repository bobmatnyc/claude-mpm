from pathlib import Path

"""
Dependency caching system for smart dependency checking.

This module provides caching for dependency check results to avoid
redundant checks and improve startup performance.
"""

import hashlib
import json
import time
from typing import Dict, Optional, Tuple

from ..core.logger import get_logger

logger = get_logger(__name__)


class DependencyCache:
    """
    Manages caching of dependency check results.

    WHY: Dependency checking can be slow, especially when checking many packages.
    By caching results keyed by deployment hash, we can skip checks when nothing
    has changed, significantly improving startup time.

    DESIGN DECISION: We use a file-based cache in .claude/agents/.dependency_cache
    - Simple JSON format for easy debugging
    - TTL-based expiration (24 hours default)
    - Automatic invalidation when agent deployment changes
    """

    DEFAULT_TTL_SECONDS = 86400  # 24 hours

    def __init__(
        self, cache_dir: Optional[Path] = None, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ):
        """
        Initialize the dependency cache.

        Args:
            cache_dir: Directory for cache files (default: .claude/agents/)
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        if cache_dir is None:
            cache_dir = Path.cwd() / ".claude" / "agents"

        self.cache_dir = cache_dir
        self.cache_file = self.cache_dir / ".dependency_cache"
        self.ttl_seconds = ttl_seconds
        self._cache_data: Optional[Dict] = None

    def _load_cache(self) -> Dict:
        """
        Load cache data from disk.

        Returns:
            Cache data dictionary or empty dict if not found.
        """
        if self._cache_data is not None:
            return self._cache_data

        if not self.cache_file.exists():
            self._cache_data = {}
            return self._cache_data

        try:
            with open(self.cache_file) as f:
                self._cache_data = json.load(f)
                return self._cache_data
        except Exception as e:
            logger.debug(f"Could not load dependency cache: {e}")
            self._cache_data = {}
            return self._cache_data

    def _save_cache(self, cache_data: Dict) -> None:
        """
        Save cache data to disk.

        Args:
            cache_data: Cache data to save.
        """
        try:
            # Ensure directory exists
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)

            self._cache_data = cache_data
        except Exception as e:
            logger.debug(f"Could not save dependency cache: {e}")

    def _generate_cache_key(self, deployment_hash: str, context: Dict) -> str:
        """
        Generate a cache key for dependency results.

        Args:
            deployment_hash: Hash of the current agent deployment
            context: Additional context (e.g., Python version, platform)

        Returns:
            Cache key string.

        WHY: We include context like Python version because dependency
        availability can vary between Python versions.
        """
        # Include important context in the cache key
        import platform
        import sys

        key_parts = [
            deployment_hash,
            f"py{sys.version_info.major}.{sys.version_info.minor}",
            platform.system().lower(),
            platform.machine().lower(),
        ]

        # Add any additional context
        for key, value in sorted(context.items()):
            key_parts.append(f"{key}:{value}")

        # Create a hash of all parts for a compact key
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(
        self, deployment_hash: str, context: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Get cached dependency check results.

        Args:
            deployment_hash: Hash of the current agent deployment
            context: Additional context for cache key

        Returns:
            Cached results or None if not found/expired.
        """
        if context is None:
            context = {}

        cache_data = self._load_cache()
        cache_key = self._generate_cache_key(deployment_hash, context)

        if cache_key not in cache_data:
            logger.debug(f"Cache miss for key {cache_key}")
            return None

        entry = cache_data[cache_key]

        # Check if entry has expired
        current_time = time.time()
        if current_time - entry.get("timestamp", 0) > self.ttl_seconds:
            logger.debug(f"Cache entry expired for key {cache_key}")
            # Remove expired entry
            del cache_data[cache_key]
            self._save_cache(cache_data)
            return None

        logger.debug(f"Cache hit for key {cache_key}")
        return entry.get("results")

    def set(
        self, deployment_hash: str, results: Dict, context: Optional[Dict] = None
    ) -> None:
        """
        Cache dependency check results.

        Args:
            deployment_hash: Hash of the current agent deployment
            results: Dependency check results to cache
            context: Additional context for cache key
        """
        if context is None:
            context = {}

        cache_data = self._load_cache()
        cache_key = self._generate_cache_key(deployment_hash, context)

        # Store with timestamp
        cache_data[cache_key] = {
            "timestamp": time.time(),
            "results": results,
            "deployment_hash": deployment_hash,
            "context": context,
        }

        # Clean up old entries while we're at it
        self._cleanup_expired_entries(cache_data)

        self._save_cache(cache_data)
        logger.debug(f"Cached results for key {cache_key}")

    def invalidate(self, deployment_hash: Optional[str] = None) -> None:
        """
        Invalidate cache entries.

        Args:
            deployment_hash: If provided, only invalidate entries for this hash.
                           If None, invalidate all entries.
        """
        if deployment_hash is None:
            # Clear entire cache
            self._cache_data = {}
            self._save_cache({})
            logger.info("Cleared entire dependency cache")
        else:
            # Clear entries for specific deployment
            cache_data = self._load_cache()
            keys_to_remove = []

            for key, entry in cache_data.items():
                if entry.get("deployment_hash") == deployment_hash:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del cache_data[key]

            if keys_to_remove:
                self._save_cache(cache_data)
                logger.info(
                    f"Invalidated {len(keys_to_remove)} cache entries for deployment {deployment_hash[:8]}..."
                )

    def _cleanup_expired_entries(self, cache_data: Dict) -> None:
        """
        Remove expired entries from cache data.

        Args:
            cache_data: Cache data dictionary to clean.

        WHY: We clean up expired entries periodically to prevent the cache
        from growing indefinitely.
        """
        current_time = time.time()
        keys_to_remove = []

        for key, entry in cache_data.items():
            if current_time - entry.get("timestamp", 0) > self.ttl_seconds:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del cache_data[key]

        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} expired cache entries")

    def get_cache_stats(self) -> Dict:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics.
        """
        cache_data = self._load_cache()
        current_time = time.time()

        total_entries = len(cache_data)
        expired_entries = 0
        valid_entries = 0

        for entry in cache_data.values():
            if current_time - entry.get("timestamp", 0) > self.ttl_seconds:
                expired_entries += 1
            else:
                valid_entries += 1

        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_file": str(self.cache_file),
            "ttl_seconds": self.ttl_seconds,
        }

    def clear(self) -> None:
        """
        Clear all cache entries.
        """
        self.invalidate(None)


class SmartDependencyChecker:
    """
    Combines caching with agent dependency checking for smart, efficient checks.

    WHY: This class orchestrates the smart dependency checking by combining:
    - Change detection (only check when agents change)
    - Caching (reuse results when nothing has changed)
    - Environment awareness (only prompt in appropriate contexts)
    """

    def __init__(self, cache_ttl_seconds: int = DependencyCache.DEFAULT_TTL_SECONDS):
        """
        Initialize the smart dependency checker.

        Args:
            cache_ttl_seconds: TTL for cache entries.
        """
        self.cache = DependencyCache(ttl_seconds=cache_ttl_seconds)
        self._last_check_time = 0
        self._min_check_interval = 60  # Don't check more than once per minute

    def should_check_dependencies(
        self, force_check: bool = False, deployment_hash: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Determine if dependency checking should be performed.

        Args:
            force_check: Force checking regardless of cache/changes
            deployment_hash: Current deployment hash

        Returns:
            Tuple of (should_check, reason)
        """
        if force_check:
            return True, "Forced check requested"

        # Rate limiting - don't check too frequently
        current_time = time.time()
        if current_time - self._last_check_time < self._min_check_interval:
            return False, f"Checked recently (within {self._min_check_interval}s)"

        # Check if we have valid cached results
        if deployment_hash:
            cached_results = self.cache.get(deployment_hash)
            if cached_results:
                return False, "Valid cached results available"

        return True, "No valid cache, checking needed"

    def get_or_check_dependencies(
        self, loader, force_check: bool = False  # AgentDependencyLoader instance
    ) -> Tuple[Dict, bool]:
        """
        Get dependency results from cache or perform check.

        Args:
            loader: AgentDependencyLoader instance
            force_check: Force checking even if cached

        Returns:
            Tuple of (results, was_cached)
        """
        # Check if agents have changed
        has_changed, deployment_hash = loader.has_agents_changed()

        # Try to get cached results first
        if not force_check and not has_changed:
            cached_results = self.cache.get(deployment_hash)
            if cached_results:
                logger.info("Using cached dependency check results")
                return cached_results, True

        # Perform actual dependency check
        logger.info("Performing dependency check...")
        results = loader.load_and_check()

        # Cache the results
        self.cache.set(deployment_hash, results)

        # Mark deployment as checked
        loader.mark_deployment_checked(deployment_hash, results)

        # Update last check time
        self._last_check_time = time.time()

        return results, False
