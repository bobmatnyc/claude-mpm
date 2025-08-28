"""
Cache Manager Service for Framework Loader
==========================================

WHY: This service extracts and centralizes cache management logic from the FrameworkLoader,
providing a clean interface for managing multiple cache types with different TTLs.

DESIGN DECISION: Built on top of the existing FileSystemCache infrastructure while
providing a specialized interface for framework-specific caching needs.

EXTRACTED FROM: core/framework_loader.py (lines 89-140)
- Reduces FrameworkLoader complexity by ~50 lines
- Provides thread-safe, type-specific cache management

NOTE: The ICacheManager interface has been moved to service_interfaces.py for
better organization and to support dependency injection.
"""

import threading
import time
from typing import Any, Dict, Optional, Set, Tuple

from claude_mpm.core.cache import FileSystemCache
from claude_mpm.core.logger import get_logger

# Import interface from consolidated location
from .service_interfaces import ICacheManager


class CacheManager(ICacheManager):
    """
    Centralized cache management service for framework loader.

    This service manages multiple cache types with different TTLs:
    - Agent capabilities (60s TTL)
    - Deployed agents (30s TTL)
    - Agent metadata (60s TTL)
    - Memories (60s TTL)

    Thread-safe implementation using locks for concurrent access.
    """

    # Default TTL values (in seconds)
    DEFAULT_CAPABILITIES_TTL = 60
    DEFAULT_DEPLOYED_AGENTS_TTL = 30
    DEFAULT_METADATA_TTL = 60
    DEFAULT_MEMORIES_TTL = 60

    def __init__(
        self,
        capabilities_ttl: float = DEFAULT_CAPABILITIES_TTL,
        deployed_agents_ttl: float = DEFAULT_DEPLOYED_AGENTS_TTL,
        metadata_ttl: float = DEFAULT_METADATA_TTL,
        memories_ttl: float = DEFAULT_MEMORIES_TTL,
    ):
        """
        Initialize cache manager with configurable TTLs.

        Args:
            capabilities_ttl: TTL for agent capabilities cache
            deployed_agents_ttl: TTL for deployed agents cache
            metadata_ttl: TTL for agent metadata cache
            memories_ttl: TTL for memories cache
        """
        self.logger = get_logger("cache_manager")

        # TTL configuration
        self.capabilities_ttl = capabilities_ttl
        self.deployed_agents_ttl = deployed_agents_ttl
        self.metadata_ttl = metadata_ttl
        self.memories_ttl = memories_ttl

        # Cache storage with timestamps
        self._capabilities_cache: Optional[str] = None
        self._capabilities_cache_time: float = 0

        self._deployed_agents_cache: Optional[Set[str]] = None
        self._deployed_agents_cache_time: float = 0

        self._agent_metadata_cache: Dict[
            str, Tuple[Optional[Dict[str, Any]], float]
        ] = {}

        self._memories_cache: Optional[Dict[str, Any]] = None
        self._memories_cache_time: float = 0

        # Thread safety
        self._lock = threading.RLock()

        # Underlying file system cache (optional, for persistence)
        self._fs_cache = FileSystemCache(
            max_size_mb=50,  # 50MB for framework caches
            default_ttl=max(
                capabilities_ttl, deployed_agents_ttl, metadata_ttl, memories_ttl
            ),
        )

        self.logger.debug(
            f"Cache manager initialized with TTLs: "
            f"capabilities={capabilities_ttl}s, "
            f"deployed_agents={deployed_agents_ttl}s, "
            f"metadata={metadata_ttl}s, "
            f"memories={memories_ttl}s"
        )

    def is_cache_valid(self, cache_time: float, ttl: float) -> bool:
        """Check if a cache entry is still valid based on its timestamp and TTL."""
        current_time = time.time()
        age = current_time - cache_time
        return age < ttl

    # Agent capabilities cache
    def get_capabilities(self) -> Optional[str]:
        """Get cached agent capabilities."""
        with self._lock:
            if self._capabilities_cache is not None and self.is_cache_valid(
                self._capabilities_cache_time, self.capabilities_ttl
            ):
                age = time.time() - self._capabilities_cache_time
                self.logger.debug(f"Cache hit: agent capabilities (age: {age:.1f}s)")
                return self._capabilities_cache

            self.logger.debug("Cache miss: agent capabilities")
            return None

    def set_capabilities(self, value: str) -> None:
        """Set agent capabilities cache."""
        with self._lock:
            self._capabilities_cache = value
            self._capabilities_cache_time = time.time()
            self.logger.debug("Updated agent capabilities cache")

    # Deployed agents cache
    def get_deployed_agents(self) -> Optional[Set[str]]:
        """Get cached deployed agents set."""
        with self._lock:
            if self._deployed_agents_cache is not None and self.is_cache_valid(
                self._deployed_agents_cache_time, self.deployed_agents_ttl
            ):
                age = time.time() - self._deployed_agents_cache_time
                self.logger.debug(f"Cache hit: deployed agents (age: {age:.1f}s)")
                return (
                    self._deployed_agents_cache.copy()
                )  # Return a copy to prevent external modification

            self.logger.debug("Cache miss: deployed agents")
            return None

    def set_deployed_agents(self, agents: Set[str]) -> None:
        """Set deployed agents cache."""
        with self._lock:
            self._deployed_agents_cache = agents.copy()  # Store a copy
            self._deployed_agents_cache_time = time.time()
            self.logger.debug(
                f"Updated deployed agents cache with {len(agents)} agents"
            )

    # Agent metadata cache
    def get_agent_metadata(
        self, agent_file: str
    ) -> Optional[Tuple[Optional[Dict[str, Any]], float]]:
        """Get cached agent metadata for a specific file."""
        with self._lock:
            if agent_file in self._agent_metadata_cache:
                cached_data, cached_mtime = self._agent_metadata_cache[agent_file]
                # Check if cache is still valid
                if self.is_cache_valid(cached_mtime, self.metadata_ttl):
                    self.logger.debug(f"Cache hit: metadata for {agent_file}")
                    return cached_data, cached_mtime

            self.logger.debug(f"Cache miss: metadata for {agent_file}")
            return None

    def set_agent_metadata(
        self, agent_file: str, metadata: Optional[Dict[str, Any]], mtime: float
    ) -> None:
        """Set agent metadata cache for a specific file."""
        with self._lock:
            self._agent_metadata_cache[agent_file] = (metadata, mtime)
            self.logger.debug(f"Updated metadata cache for {agent_file}")

    # Memories cache
    def get_memories(self) -> Optional[Dict[str, Any]]:
        """Get cached memories."""
        with self._lock:
            if self._memories_cache is not None and self.is_cache_valid(
                self._memories_cache_time, self.memories_ttl
            ):
                age = time.time() - self._memories_cache_time
                self.logger.debug(f"Cache hit: memories (age: {age:.1f}s)")
                return self._memories_cache.copy()  # Return a copy

            self.logger.debug("Cache miss: memories")
            return None

    def set_memories(self, memories: Dict[str, Any]) -> None:
        """Set memories cache."""
        with self._lock:
            self._memories_cache = memories.copy()  # Store a copy
            self._memories_cache_time = time.time()
            self.logger.debug("Updated memories cache")

    # Cache clearing methods
    def clear_all(self) -> None:
        """Clear all caches."""
        with self._lock:
            self.logger.info("Clearing all caches")

            # Clear capabilities
            self._capabilities_cache = None
            self._capabilities_cache_time = 0

            # Clear deployed agents
            self._deployed_agents_cache = None
            self._deployed_agents_cache_time = 0

            # Clear metadata
            self._agent_metadata_cache.clear()

            # Clear memories
            self._memories_cache = None
            self._memories_cache_time = 0

            # Clear underlying file system cache
            self._fs_cache.clear()

    def clear_agent_caches(self) -> None:
        """Clear agent-related caches only."""
        with self._lock:
            self.logger.info("Clearing agent-related caches")

            # Clear capabilities
            self._capabilities_cache = None
            self._capabilities_cache_time = 0

            # Clear deployed agents
            self._deployed_agents_cache = None
            self._deployed_agents_cache_time = 0

            # Clear metadata
            self._agent_metadata_cache.clear()

    def clear_memory_caches(self) -> None:
        """Clear memory-related caches only."""
        with self._lock:
            self.logger.info("Clearing memory caches")

            self._memories_cache = None
            self._memories_cache_time = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            current_time = time.time()

            return {
                "capabilities": {
                    "cached": self._capabilities_cache is not None,
                    "age": (
                        current_time - self._capabilities_cache_time
                        if self._capabilities_cache
                        else None
                    ),
                    "valid": (
                        self.is_cache_valid(
                            self._capabilities_cache_time, self.capabilities_ttl
                        )
                        if self._capabilities_cache
                        else False
                    ),
                },
                "deployed_agents": {
                    "cached": self._deployed_agents_cache is not None,
                    "count": (
                        len(self._deployed_agents_cache)
                        if self._deployed_agents_cache
                        else 0
                    ),
                    "age": (
                        current_time - self._deployed_agents_cache_time
                        if self._deployed_agents_cache
                        else None
                    ),
                    "valid": (
                        self.is_cache_valid(
                            self._deployed_agents_cache_time, self.deployed_agents_ttl
                        )
                        if self._deployed_agents_cache
                        else False
                    ),
                },
                "metadata": {"entries": len(self._agent_metadata_cache)},
                "memories": {
                    "cached": self._memories_cache is not None,
                    "age": (
                        current_time - self._memories_cache_time
                        if self._memories_cache
                        else None
                    ),
                    "valid": (
                        self.is_cache_valid(
                            self._memories_cache_time, self.memories_ttl
                        )
                        if self._memories_cache
                        else False
                    ),
                },
                "fs_cache": self._fs_cache.get_stats() if self._fs_cache else {},
            }
