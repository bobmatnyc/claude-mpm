"""
Consolidated Core Service Interfaces
====================================

WHY: This module consolidates all core service interfaces from across the codebase
to provide a single source of truth for service contracts. This enables better
dependency injection and service management.

DESIGN DECISION: Rather than having interfaces scattered across multiple files,
we consolidate them here while maintaining backward compatibility through imports
in the original locations.

INCLUDES:
- ICacheManager (from cache_manager.py)
- IPathResolver (new)
- IMemoryManager (new)
- IFrameworkLoader (new)
- Other core service interfaces needed for DI
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Import CLI service interfaces

# Re-export infrastructure interfaces for convenience


# Cache Manager Interface (moved from cache_manager.py)
class ICacheManager(ABC):
    """Interface for framework-specific cache management service."""

    @abstractmethod
    def get_capabilities(self) -> Optional[str]:
        """Get cached agent capabilities."""

    @abstractmethod
    def set_capabilities(self, value: str) -> None:
        """Set agent capabilities cache."""

    @abstractmethod
    def get_deployed_agents(self) -> Optional[Set[str]]:
        """Get cached deployed agents set."""

    @abstractmethod
    def set_deployed_agents(self, agents: Set[str]) -> None:
        """Set deployed agents cache."""

    @abstractmethod
    def get_agent_metadata(
        self, agent_file: str
    ) -> Optional[Tuple[Optional[Dict[str, Any]], float]]:
        """Get cached agent metadata for a specific file."""

    @abstractmethod
    def set_agent_metadata(
        self, agent_file: str, metadata: Optional[Dict[str, Any]], mtime: float
    ) -> None:
        """Set agent metadata cache for a specific file."""

    @abstractmethod
    def get_memories(self) -> Optional[Dict[str, Any]]:
        """Get cached memories."""

    @abstractmethod
    def set_memories(self, memories: Dict[str, Any]) -> None:
        """Set memories cache."""

    @abstractmethod
    def clear_all(self) -> None:
        """Clear all caches."""

    @abstractmethod
    def clear_agent_caches(self) -> None:
        """Clear agent-related caches only."""

    @abstractmethod
    def clear_memory_caches(self) -> None:
        """Clear memory-related caches only."""

    @abstractmethod
    def is_cache_valid(self, cache_time: float, ttl: float) -> bool:
        """Check if a cache entry is still valid based on its timestamp and TTL."""


# Path Resolution Interface
class IPathResolver(ABC):
    """Interface for path resolution and validation service."""

    @abstractmethod
    def resolve_path(self, path: str, base_dir: Optional[Path] = None) -> Path:
        """
        Resolve a path relative to a base directory.

        Args:
            path: The path to resolve (can be relative or absolute)
            base_dir: Base directory for relative paths (defaults to cwd)

        Returns:
            The resolved absolute path
        """

    @abstractmethod
    def validate_path(self, path: Path, must_exist: bool = False) -> bool:
        """
        Validate a path for security and existence.

        Args:
            path: The path to validate
            must_exist: Whether the path must exist

        Returns:
            True if path is valid, False otherwise
        """

    @abstractmethod
    def ensure_directory(self, path: Path) -> Path:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: The directory path

        Returns:
            The directory path
        """

    @abstractmethod
    def find_project_root(self, start_path: Optional[Path] = None) -> Optional[Path]:
        """
        Find the project root directory.

        Args:
            start_path: Starting path for search (defaults to cwd)

        Returns:
            Project root path or None if not found
        """


# Memory Management Interface
class IMemoryManager(ABC):
    """Interface for agent memory management service."""

    @abstractmethod
    def load_memories(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load memories for an agent or all agents.

        Args:
            agent_name: Specific agent name or None for all

        Returns:
            Dictionary of memories
        """

    @abstractmethod
    def save_memory(
        self, key: str, value: Any, agent_name: Optional[str] = None
    ) -> None:
        """
        Save a memory entry.

        Args:
            key: Memory key
            value: Memory value
            agent_name: Agent name or None for global
        """

    @abstractmethod
    def search_memories(
        self, query: str, agent_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memories by query.

        Args:
            query: Search query
            agent_name: Specific agent or None for all

        Returns:
            List of matching memory entries
        """

    @abstractmethod
    def clear_memories(self, agent_name: Optional[str] = None) -> None:
        """
        Clear memories for an agent or all agents.

        Args:
            agent_name: Specific agent or None for all
        """

    @abstractmethod
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics.

        Returns:
            Dictionary with memory statistics
        """


# Framework Loader Interface
class IFrameworkLoader(ABC):
    """Interface for framework loading and instruction management."""

    @abstractmethod
    def load_instructions(self) -> str:
        """
        Load and format framework instructions.

        Returns:
            Formatted instructions for injection
        """

    @abstractmethod
    def get_agent_capabilities(self) -> str:
        """
        Get formatted agent capabilities.

        Returns:
            Agent capabilities text
        """

    @abstractmethod
    def get_deployed_agents(self) -> Set[str]:
        """
        Get set of deployed agent names.

        Returns:
            Set of agent names
        """

    @abstractmethod
    def reload(self) -> None:
        """Reload framework instructions and clear caches."""

    @abstractmethod
    def get_version(self) -> Optional[str]:
        """
        Get framework version.

        Returns:
            Version string or None
        """


# File System Service Interface
class IFileSystemService(ABC):
    """Interface for file system operations."""

    @abstractmethod
    def read_file(self, path: Path, encoding: str = "utf-8") -> str:
        """
        Read file contents.

        Args:
            path: File path
            encoding: File encoding

        Returns:
            File contents
        """

    @abstractmethod
    def write_file(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        """
        Write content to file.

        Args:
            path: File path
            content: Content to write
            encoding: File encoding
        """

    @abstractmethod
    def copy_file(self, source: Path, destination: Path) -> None:
        """
        Copy file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path
        """

    @abstractmethod
    def delete_file(self, path: Path) -> bool:
        """
        Delete a file.

        Args:
            path: File path

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    def list_directory(self, path: Path, pattern: Optional[str] = None) -> List[Path]:
        """
        List directory contents.

        Args:
            path: Directory path
            pattern: Optional glob pattern

        Returns:
            List of paths
        """


# Environment Service Interface
class IEnvironmentService(ABC):
    """Interface for environment and configuration management."""

    @abstractmethod
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable.

        Args:
            key: Environment variable key
            default: Default value if not found

        Returns:
            Environment value or default
        """

    @abstractmethod
    def set_env(self, key: str, value: str) -> None:
        """
        Set environment variable.

        Args:
            key: Environment variable key
            value: Value to set
        """

    @abstractmethod
    def get_config_dir(self) -> Path:
        """
        Get configuration directory.

        Returns:
            Configuration directory path
        """

    @abstractmethod
    def get_data_dir(self) -> Path:
        """
        Get data directory.

        Returns:
            Data directory path
        """

    @abstractmethod
    def get_cache_dir(self) -> Path:
        """
        Get cache directory.

        Returns:
            Cache directory path
        """


# Process Management Interface
class IProcessManager(ABC):
    """Interface for process and subprocess management."""

    @abstractmethod
    def run_command(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[int, str, str]:
        """
        Run a command and return result.

        Args:
            command: Command and arguments
            cwd: Working directory
            env: Environment variables
            timeout: Command timeout in seconds

        Returns:
            Tuple of (return_code, stdout, stderr)
        """

    @abstractmethod
    def start_process(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Start a background process.

        Args:
            command: Command and arguments
            cwd: Working directory
            env: Environment variables

        Returns:
            Process ID
        """

    @abstractmethod
    def stop_process(self, pid: int, timeout: float = 5.0) -> bool:
        """
        Stop a process.

        Args:
            pid: Process ID
            timeout: Timeout for graceful shutdown

        Returns:
            True if stopped successfully
        """

    @abstractmethod
    def is_process_running(self, pid: int) -> bool:
        """
        Check if process is running.

        Args:
            pid: Process ID

        Returns:
            True if process is running
        """
