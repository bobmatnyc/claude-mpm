"""
Centralized path management for claude-mpm.

This module provides the primary interface for path management operations.
All functionality has been consolidated into the unified path management system.

This module provides a consistent, reliable way to access project paths
without fragile parent.parent.parent patterns.
"""

from pathlib import Path
from typing import Optional, Union

from claude_mpm.core.logging_utils import get_logger

# Import from the unified path management system
from ..core.unified_paths import get_path_manager

logger = get_logger(__name__)


class ClaudeMPMPaths:
    """
    Primary interface for the unified path management system.

    This class provides access to all path operations through the UnifiedPathManager.

    Usage:
        from claude_mpm.config.paths import paths

        # Access common paths
        project_root = paths.project_root
        agents_dir = paths.agents_dir
        config_file = paths.config_dir / "some_config.yaml"
    """

    _instance: Optional["ClaudeMPMPaths"] = None
    _path_manager = None

    def __new__(cls) -> "ClaudeMPMPaths":
        """Singleton pattern to ensure single instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize paths using the unified path manager."""
        if self._path_manager is None:
            self._path_manager = get_path_manager()

    # ========================================================================
    # Compatibility Properties - Delegate to UnifiedPathManager
    # ========================================================================

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return self._path_manager.project_root

    @property
    def framework_root(self) -> Path:
        """Get the framework root directory."""
        return self._path_manager.framework_root

    @property
    def src_dir(self) -> Path:
        """Get the src directory."""
        return self._path_manager.framework_root / "src"

    @property
    def claude_mpm_dir(self) -> Path:
        """Get the main claude_mpm package directory."""
        return self._path_manager.package_root

    @property
    def agents_dir(self) -> Path:
        """Get the agents directory."""
        return self._path_manager.get_agents_dir("framework")

    @property
    def services_dir(self) -> Path:
        """Get the services directory."""
        return self._path_manager.package_root / "services"

    @property
    def hooks_dir(self) -> Path:
        """Get the hooks directory."""
        return self._path_manager.package_root / "hooks"

    @property
    def config_dir(self) -> Path:
        """Get the config directory."""
        return self._path_manager.package_root / "config"

    @property
    def cli_dir(self) -> Path:
        """Get the CLI directory."""
        return self._path_manager.package_root / "cli"

    @property
    def core_dir(self) -> Path:
        """Get the core directory."""
        return self._path_manager.package_root / "core"

    @property
    def schemas_dir(self) -> Path:
        """Get the schemas directory."""
        return self._path_manager.package_root / "schemas"

    @property
    def scripts_dir(self) -> Path:
        """Get the scripts directory."""
        return self._path_manager.get_scripts_dir()

    @property
    def tests_dir(self) -> Path:
        """Get the tests directory."""
        return self._path_manager.project_root / "tests"

    @property
    def docs_dir(self) -> Path:
        """Get the documentation directory."""
        return self._path_manager.project_root / "docs"

    @property
    def logs_dir(self) -> Path:
        """Get the logs directory (creates if doesn't exist)."""
        logs_dir = self._path_manager.get_logs_dir("project")
        self._path_manager.ensure_directory(logs_dir)
        return logs_dir

    @property
    def temp_dir(self) -> Path:
        """Get the temporary files directory (creates if doesn't exist)."""
        temp_dir = self._path_manager.project_root / ".tmp"
        self._path_manager.ensure_directory(temp_dir)
        return temp_dir

    @property
    def claude_mpm_dir_hidden(self) -> Path:
        """Get the hidden .claude-mpm directory (creates if doesn't exist)."""
        hidden_dir = self._path_manager.get_config_dir("project")
        self._path_manager.ensure_directory(hidden_dir)
        return hidden_dir

    @property
    def version_file(self) -> Path:
        """Get the VERSION file path."""
        return self._path_manager.project_root / "VERSION"

    @property
    def pyproject_file(self) -> Path:
        """Get the pyproject.toml file path."""
        return self._path_manager.project_root / "pyproject.toml"

    @property
    def package_json_file(self) -> Path:
        """Get the package.json file path."""
        return self._path_manager.project_root / "package.json"

    @property
    def claude_md_file(self) -> Path:
        """Get the CLAUDE.md file path."""
        return self._path_manager.project_root / "CLAUDE.md"

    def get_version(self) -> str:
        """Get the project version from various sources."""
        return self._path_manager.get_version()

    def ensure_in_path(self) -> None:
        """Ensure src directory is in Python path."""
        self._path_manager.ensure_src_in_path()

    def relative_to_project(self, path: Union[str, Path]) -> Path:
        """Get a path relative to the project root."""
        abs_path = Path(path).resolve()
        try:
            return abs_path.relative_to(self.project_root)
        except ValueError:
            return abs_path

    def resolve_config_path(self, config_name: str) -> Path:
        """Resolve a configuration file path."""
        # Check in config directory first
        config_path = self.config_dir / config_name
        if config_path.exists():
            return config_path

        # Check in project root
        root_path = self.project_root / config_name
        if root_path.exists():
            return root_path

        # Return config dir path as default
        return config_path

    def __str__(self) -> str:
        """String representation."""
        return f"ClaudeMPMPaths(root={self.project_root})"

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"ClaudeMPMPaths(\n"
            f"  project_root={self.project_root},\n"
            f"  src_dir={self.src_dir},\n"
            f"  claude_mpm_dir={self.claude_mpm_dir}\n"
            f")"
        )


# Singleton instance for import
paths = ClaudeMPMPaths()


# Convenience functions
def get_project_root() -> Path:
    """Get the project root directory."""
    return paths.project_root


def get_src_dir() -> Path:
    """Get the src directory."""
    return paths.src_dir


def get_claude_mpm_dir() -> Path:
    """Get the main claude_mpm package directory."""
    return paths.claude_mpm_dir


def get_agents_dir() -> Path:
    """Get the agents directory."""
    return paths.agents_dir


def get_services_dir() -> Path:
    """Get the services directory."""
    return paths.services_dir


def get_config_dir() -> Path:
    """Get the config directory."""
    return paths.config_dir


def get_version() -> str:
    """Get the project version."""
    return paths.get_version()


def ensure_src_in_path() -> None:
    """Ensure src directory is in Python path."""
    paths.ensure_in_path()


# Auto-ensure src is in path when module is imported
ensure_src_in_path()
