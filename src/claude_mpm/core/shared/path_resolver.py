"""
Shared path resolution utilities to reduce duplication.
"""

import os
from pathlib import Path
from typing import List, Optional, Union

from ..logger import get_logger


class PathResolver:
    """
    Centralized path resolution utility.

    Reduces duplication by providing standard patterns for:
    - Working directory resolution
    - Configuration directory discovery
    - Agent directory resolution
    - Memory directory resolution
    """

    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        """
        Initialize path resolver.

        Args:
            base_dir: Base directory for relative paths
        """
        self.base_dir = Path(base_dir) if base_dir else self._get_working_dir()
        self.logger = get_logger("path_resolver")

    def _get_working_dir(self) -> Path:
        """Get working directory respecting CLAUDE_MPM_USER_PWD."""
        # Use CLAUDE_MPM_USER_PWD if available (when called via shell script)
        user_pwd = os.environ.get("CLAUDE_MPM_USER_PWD")
        if user_pwd:
            return Path(user_pwd)
        return Path.cwd()

    def resolve_config_dir(self, create: bool = False) -> Path:
        """
        Resolve configuration directory.

        Args:
            create: Whether to create directory if it doesn't exist

        Returns:
            Path to configuration directory
        """
        config_dir = self.base_dir / ".claude-mpm"

        if create and not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created config directory: {config_dir}")

        return config_dir

    def resolve_agents_dir(self, create: bool = False) -> Path:
        """
        Resolve agents directory.

        Args:
            create: Whether to create directory if it doesn't exist

        Returns:
            Path to agents directory
        """
        agents_dir = self.resolve_config_dir(create) / "agents"

        if create and not agents_dir.exists():
            agents_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created agents directory: {agents_dir}")

        return agents_dir

    def resolve_memories_dir(self, create: bool = False) -> Path:
        """
        Resolve memories directory.

        Args:
            create: Whether to create directory if it doesn't exist

        Returns:
            Path to memories directory
        """
        memories_dir = self.resolve_config_dir(create) / "memories"

        if create and not memories_dir.exists():
            memories_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created memories directory: {memories_dir}")

        return memories_dir

    def resolve_logs_dir(self, create: bool = False) -> Path:
        """
        Resolve logs directory.

        Args:
            create: Whether to create directory if it doesn't exist

        Returns:
            Path to logs directory
        """
        logs_dir = self.resolve_config_dir(create) / "logs"

        if create and not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created logs directory: {logs_dir}")

        return logs_dir

    def resolve_temp_dir(self, create: bool = False) -> Path:
        """
        Resolve temporary directory.

        Args:
            create: Whether to create directory if it doesn't exist

        Returns:
            Path to temporary directory
        """
        temp_dir = self.resolve_config_dir(create) / "tmp"

        if create and not temp_dir.exists():
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created temp directory: {temp_dir}")

        return temp_dir

    def find_agent_file(
        self, agent_name: str, filename: Optional[str] = None
    ) -> Optional[Path]:
        """
        Find agent file in standard locations.

        Args:
            agent_name: Name of the agent
            filename: Specific filename to look for (defaults to agent_name.md)

        Returns:
            Path to agent file if found
        """
        if filename is None:
            filename = f"{agent_name}.md"

        # Search locations in order of preference
        search_paths = [
            self.resolve_agents_dir(),  # Project agents
            Path.home() / ".claude" / "agents",  # User agents
            self.base_dir / "agents",  # Local agents directory
            self.base_dir,  # Current directory
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            agent_file = search_path / filename
            if agent_file.exists() and agent_file.is_file():
                self.logger.debug(f"Found agent file: {agent_file}")
                return agent_file

        return None

    def find_memory_file(
        self, agent_name: str, filename: Optional[str] = None
    ) -> Optional[Path]:
        """
        Find memory file for an agent.

        Args:
            agent_name: Name of the agent
            filename: Specific filename to look for (defaults to agent_name.md)

        Returns:
            Path to memory file if found
        """
        if filename is None:
            filename = f"{agent_name}.md"

        memories_dir = self.resolve_memories_dir()
        memory_file = memories_dir / filename

        if memory_file.exists() and memory_file.is_file():
            return memory_file

        return None

    def find_config_file(
        self, filename: str, search_paths: Optional[List[Union[str, Path]]] = None
    ) -> Optional[Path]:
        """
        Find configuration file in standard locations.

        Args:
            filename: Configuration filename
            search_paths: Additional search paths

        Returns:
            Path to configuration file if found
        """
        default_paths = [
            self.resolve_config_dir(),
            self.base_dir,
            Path.home() / ".claude-mpm",
        ]

        if search_paths:
            all_paths = [Path(p) for p in search_paths] + default_paths
        else:
            all_paths = default_paths

        for search_path in all_paths:
            if not search_path.exists():
                continue

            config_file = search_path / filename
            if config_file.exists() and config_file.is_file():
                self.logger.debug(f"Found config file: {config_file}")
                return config_file

        return None

    def ensure_directory(self, path: Union[str, Path]) -> Path:
        """
        Ensure directory exists.

        Args:
            path: Directory path

        Returns:
            Path object for the directory
        """
        dir_path = Path(path)

        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {dir_path}")
        elif not dir_path.is_dir():
            raise ValueError(f"Path exists but is not a directory: {dir_path}")

        return dir_path

    def resolve_relative_path(self, path: Union[str, Path]) -> Path:
        """
        Resolve path relative to base directory.

        Args:
            path: Path to resolve

        Returns:
            Resolved absolute path
        """
        path_obj = Path(path)

        if path_obj.is_absolute():
            return path_obj

        return (self.base_dir / path_obj).resolve()

    def get_path_info(self) -> dict:
        """
        Get information about resolved paths.

        Returns:
            Dictionary with path information
        """
        return {
            "base_dir": str(self.base_dir),
            "config_dir": str(self.resolve_config_dir()),
            "agents_dir": str(self.resolve_agents_dir()),
            "memories_dir": str(self.resolve_memories_dir()),
            "logs_dir": str(self.resolve_logs_dir()),
            "temp_dir": str(self.resolve_temp_dir()),
            "working_dir_from_env": os.environ.get("CLAUDE_MPM_USER_PWD"),
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"PathResolver(base_dir={self.base_dir})"
