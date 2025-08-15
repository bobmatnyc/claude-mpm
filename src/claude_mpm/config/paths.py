"""
Centralized path management for claude-mpm.

This module provides a consistent, reliable way to access project paths
without fragile parent.parent.parent patterns.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union
from functools import cached_property
import logging

logger = logging.getLogger(__name__)


class ClaudeMPMPaths:
    """
    Centralized path management for the claude-mpm project.
    
    This class provides a singleton instance with properties for all common paths
    in the project, eliminating the need for fragile Path(__file__).parent.parent patterns.
    
    Usage:
        from claude_mpm.config.paths import paths
        
        # Access common paths
        project_root = paths.project_root
        agents_dir = paths.agents_dir
        config_file = paths.config_dir / "some_config.yaml"
    """
    
    _instance: Optional['ClaudeMPMPaths'] = None
    _project_root: Optional[Path] = None
    _is_installed: bool = False
    
    def __new__(cls) -> 'ClaudeMPMPaths':
        """Singleton pattern to ensure single instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize paths if not already done."""
        if self._project_root is None:
            self._is_installed = False
            self._detect_project_root()
    
    def _detect_project_root(self) -> None:
        """
        Detect the project root directory.
        
        Strategy:
        1. Look for definitive project markers (pyproject.toml, setup.py)
        2. Look for combination of markers to ensure we're at the right level
        3. Walk up from current file location
        4. Handle both development and installed environments
        """
        # Start from this file's location
        current = Path(__file__).resolve()
        
        # Check if we're in an installed environment (site-packages)
        # In pip/pipx installs, the package is directly in site-packages
        if 'site-packages' in str(current) or 'dist-packages' in str(current):
            # We're in an installed environment
            # The claude_mpm package directory itself is the "root" for resources
            import claude_mpm
            self._project_root = Path(claude_mpm.__file__).parent
            self._is_installed = True
            logger.debug(f"Installed environment detected, using package dir: {self._project_root}")
            return
        
        # We're in a development environment, look for project markers
        for parent in current.parents:
            # Check for definitive project root indicators
            # Prioritize pyproject.toml and setup.py as they're only at root
            if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
                self._project_root = parent
                self._is_installed = False
                logger.debug(f"Project root detected at: {parent} (found pyproject.toml or setup.py)")
                return
            
            # Secondary check: .git directory + VERSION file together
            # This combination is more likely to be the real project root
            if (parent / '.git').exists() and (parent / 'VERSION').exists():
                self._project_root = parent
                self._is_installed = False
                logger.debug(f"Project root detected at: {parent} (found .git and VERSION)")
                return
        
        # Fallback: walk up to find claude-mpm directory name
        for parent in current.parents:
            if parent.name == 'claude-mpm':
                self._project_root = parent
                self._is_installed = False
                logger.debug(f"Project root detected at: {parent} (by directory name)")
                return
        
        # Last resort fallback: 3 levels up from this file
        # paths.py is in src/claude_mpm/config/
        self._project_root = current.parent.parent.parent
        self._is_installed = False
        logger.warning(f"Project root fallback to: {self._project_root}")
    
    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        if self._project_root is None:
            self._detect_project_root()
        return self._project_root
    
    @property
    def src_dir(self) -> Path:
        """Get the src directory."""
        if hasattr(self, '_is_installed') and self._is_installed:
            # In installed environment, there's no src directory
            # Return the package directory itself
            return self.project_root.parent
        return self.project_root / "src"
    
    @property
    def claude_mpm_dir(self) -> Path:
        """Get the main claude_mpm package directory."""
        if hasattr(self, '_is_installed') and self._is_installed:
            # In installed environment, project_root IS the claude_mpm directory
            return self.project_root
        return self.src_dir / "claude_mpm"
    
    @property
    def agents_dir(self) -> Path:
        """Get the agents directory."""
        if hasattr(self, '_is_installed') and self._is_installed:
            # In installed environment, agents is directly under the package
            return self.project_root / "agents"
        return self.claude_mpm_dir / "agents"
    
    @property
    def services_dir(self) -> Path:
        """Get the services directory."""
        return self.claude_mpm_dir / "services"
    
    @property
    def hooks_dir(self) -> Path:
        """Get the hooks directory."""
        return self.claude_mpm_dir / "hooks"
    
    @property
    def config_dir(self) -> Path:
        """Get the config directory."""
        return self.claude_mpm_dir / "config"
    
    @property
    def cli_dir(self) -> Path:
        """Get the CLI directory."""
        return self.claude_mpm_dir / "cli"
    
    @property
    def core_dir(self) -> Path:
        """Get the core directory."""
        return self.claude_mpm_dir / "core"
    
    @property
    def schemas_dir(self) -> Path:
        """Get the schemas directory."""
        return self.claude_mpm_dir / "schemas"
    
    @property
    def scripts_dir(self) -> Path:
        """Get the scripts directory."""
        if hasattr(self, '_is_installed') and self._is_installed:
            # In installed environment, scripts might be in a different location or not exist
            # Return a path that won't cause issues but indicates it's not available
            return Path.home() / '.claude-mpm' / 'scripts'
        return self.project_root / "scripts"
    
    @property
    def tests_dir(self) -> Path:
        """Get the tests directory."""
        if hasattr(self, '_is_installed') and self._is_installed:
            # Tests aren't distributed with installed packages
            return Path.home() / '.claude-mpm' / 'tests'
        return self.project_root / "tests"
    
    @property
    def docs_dir(self) -> Path:
        """Get the documentation directory."""
        if hasattr(self, '_is_installed') and self._is_installed:
            # Docs might be installed separately or not at all
            return Path.home() / '.claude-mpm' / 'docs'
        return self.project_root / "docs"
    
    @property
    def logs_dir(self) -> Path:
        """Get the logs directory (creates if doesn't exist)."""
        if hasattr(self, '_is_installed') and self._is_installed:
            # Use user's home directory for logs in installed environment
            logs = Path.home() / '.claude-mpm' / 'logs'
        else:
            logs = self.project_root / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        return logs
    
    @property
    def temp_dir(self) -> Path:
        """Get the temporary files directory (creates if doesn't exist)."""
        if hasattr(self, '_is_installed') and self._is_installed:
            # Use user's home directory for temp files in installed environment
            temp = Path.home() / '.claude-mpm' / '.tmp'
        else:
            temp = self.project_root / ".tmp"
        temp.mkdir(parents=True, exist_ok=True)
        return temp
    
    @property
    def claude_mpm_dir_hidden(self) -> Path:
        """Get the hidden .claude-mpm directory (creates if doesn't exist)."""
        if hasattr(self, '_is_installed') and self._is_installed:
            # Use current working directory in installed environment
            hidden = Path.cwd() / ".claude-mpm"
        else:
            hidden = self.project_root / ".claude-mpm"
        hidden.mkdir(exist_ok=True)
        return hidden
    
    @cached_property
    def version_file(self) -> Path:
        """Get the VERSION file path."""
        return self.project_root / "VERSION"
    
    @cached_property
    def pyproject_file(self) -> Path:
        """Get the pyproject.toml file path."""
        return self.project_root / "pyproject.toml"
    
    @cached_property
    def package_json_file(self) -> Path:
        """Get the package.json file path."""
        return self.project_root / "package.json"
    
    @cached_property
    def claude_md_file(self) -> Path:
        """Get the CLAUDE.md file path."""
        return self.project_root / "CLAUDE.md"
    
    def get_version(self) -> str:
        """
        Get the project version from various sources.
        
        Returns:
            Version string or 'unknown' if not found.
        """
        # Try VERSION file first
        if self.version_file.exists():
            return self.version_file.read_text().strip()
        
        # Try package metadata
        try:
            from importlib.metadata import version
            return version('claude-mpm')
        except Exception:
            pass
        
        return 'unknown'
    
    def ensure_in_path(self) -> None:
        """Ensure src directory is in Python path."""
        src_str = str(self.src_dir)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)
    
    def relative_to_project(self, path: Union[str, Path]) -> Path:
        """
        Get a path relative to the project root.
        
        Args:
            path: Path to make relative
            
        Returns:
            Path relative to project root
        """
        abs_path = Path(path).resolve()
        try:
            return abs_path.relative_to(self.project_root)
        except ValueError:
            return abs_path
    
    def resolve_config_path(self, config_name: str) -> Path:
        """
        Resolve a configuration file path.
        
        Args:
            config_name: Name of the config file
            
        Returns:
            Full path to the config file
        """
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