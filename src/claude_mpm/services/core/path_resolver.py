"""
Path Resolution Service
=======================

This module provides the PathResolver service for handling all path resolution logic
that was previously embedded in FrameworkLoader. It manages:
- Framework path detection (packaged vs development)
- NPM global path resolution
- Deployment context management
- Instruction file path resolution with precedence
- Cross-platform path handling

The service consolidates path management logic while maintaining backward compatibility.
"""

import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

from claude_mpm.core.logging_utils import get_logger

from .service_interfaces import ICacheManager, IPathResolver

logger = get_logger(__name__)


class DeploymentContext(Enum):
    """Deployment context enumeration."""

    DEVELOPMENT = "development"
    EDITABLE_INSTALL = "editable_install"
    PIP_INSTALL = "pip_install"
    PIPX_INSTALL = "pipx_install"
    SYSTEM_PACKAGE = "system_package"
    UNKNOWN = "unknown"


class PathResolver(IPathResolver):
    """
    Service for resolving and managing paths in the claude-mpm framework.

    This service extracts path resolution logic from FrameworkLoader to provide
    a focused, reusable service for path management across the application.
    """

    def __init__(self, cache_manager: Optional[ICacheManager] = None):
        """
        Initialize the PathResolver service.

        Args:
            cache_manager: Optional cache manager for caching resolved paths
        """
        self.logger = get_logger("path_resolver")
        self.cache_manager = cache_manager
        self._framework_path: Optional[Path] = None
        self._deployment_context: Optional[DeploymentContext] = None
        self._path_cache: Dict[str, str] = {}  # Internal cache for paths

    def resolve_path(self, path: str, base_dir: Optional[Path] = None) -> Path:
        """
        Resolve a path relative to a base directory.

        Args:
            path: The path to resolve (can be relative or absolute)
            base_dir: Base directory for relative paths (defaults to cwd)

        Returns:
            The resolved absolute path
        """
        path_obj = Path(path)

        if path_obj.is_absolute():
            return path_obj

        if base_dir is None:
            base_dir = self._get_working_dir()

        return (base_dir / path_obj).resolve()

    def _get_working_dir(self) -> Path:
        """Get working directory respecting CLAUDE_MPM_USER_PWD.

        When Claude MPM runs from a global installation, CLAUDE_MPM_USER_PWD
        contains the user's actual working directory. This ensures project-local
        paths are resolved correctly.

        Returns:
            Path: The user's working directory
        """
        user_pwd = os.environ.get("CLAUDE_MPM_USER_PWD")
        if user_pwd:
            return Path(user_pwd)
        return Path.cwd()

    def validate_path(self, path: Path, must_exist: bool = False) -> bool:
        """
        Validate a path for security and existence.

        Args:
            path: The path to validate
            must_exist: Whether the path must exist

        Returns:
            True if path is valid, False otherwise
        """
        try:
            # Resolve to absolute path to check for path traversal
            resolved = path.resolve()

            # Check if path exists if required
            return not (must_exist and not resolved.exists())
        except (OSError, ValueError):
            return False

    def ensure_directory(self, path: Path) -> Path:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: The directory path

        Returns:
            The directory path
        """
        path = path.resolve()
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {path}")
        elif not path.is_dir():
            raise ValueError(f"Path exists but is not a directory: {path}")
        return path

    def find_project_root(self, start_path: Optional[Path] = None) -> Optional[Path]:
        """
        Find the project root directory.

        Looks for common project indicators like .git, pyproject.toml, package.json, etc.

        Args:
            start_path: Starting path for search (defaults to cwd)

        Returns:
            Project root path or None if not found
        """
        if start_path is None:
            start_path = self._get_working_dir()

        start_path = start_path.resolve()

        # If start_path is a file, use its parent directory
        if start_path.is_file():
            start_path = start_path.parent

        # Common project root indicators
        root_indicators = [
            ".git",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "package.json",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            ".claude-mpm",  # Claude MPM specific
            "CLAUDE.md",  # Claude project instructions
        ]

        current = start_path
        while current != current.parent:  # Stop at filesystem root
            for indicator in root_indicators:
                if (current / indicator).exists():
                    self.logger.debug(
                        f"Found project root at {current} (indicator: {indicator})"
                    )
                    return current
            current = current.parent

        # If no indicators found, return None
        self.logger.debug(f"No project root found from {start_path}")
        return None

    def detect_framework_path(self) -> Optional[Path]:
        """
        Auto-detect claude-mpm framework using unified path management.

        Returns:
            Path to framework root or Path("__PACKAGED__") for packaged installations,
            None if framework not found
        """
        # Check cache first
        if self._framework_path is not None:
            return self._framework_path

        # Try to use internal cache if available
        if "framework_path" in self._path_cache:
            cached_path = self._path_cache["framework_path"]
            self._framework_path = (
                Path(cached_path)
                if cached_path != "__PACKAGED__"
                else Path("__PACKAGED__")
            )
            return self._framework_path

        # Try unified path manager first
        framework_path = self._detect_via_unified_paths()
        if framework_path:
            self._cache_framework_path(framework_path)
            return framework_path

        # Fallback to package detection
        framework_path = self._detect_via_package()
        if framework_path:
            self._cache_framework_path(framework_path)
            return framework_path

        # Try development mode detection
        framework_path = self._detect_development_mode()
        if framework_path:
            self._cache_framework_path(framework_path)
            return framework_path

        # Check common locations
        framework_path = self._check_common_locations()
        if framework_path:
            self._cache_framework_path(framework_path)
            return framework_path

        self.logger.warning("Framework not found, will use minimal instructions")
        return None

    def get_npm_global_path(self) -> Optional[Path]:
        """
        Get npm global installation path for @bobmatnyc/claude-multiagent-pm.

        Returns:
            Path to npm global installation or None if not found
        """
        # Check internal cache first
        if "npm_global_path" in self._path_cache:
            cached_path = self._path_cache["npm_global_path"]
            return Path(cached_path) if cached_path != "NOT_FOUND" else None

        npm_path = self._detect_npm_global()

        # Cache the result internally
        cache_value = str(npm_path) if npm_path else "NOT_FOUND"
        self._path_cache["npm_global_path"] = cache_value

        return npm_path

    def get_deployment_context(self) -> DeploymentContext:
        """
        Get the current deployment context.

        Returns:
            The detected deployment context
        """
        if self._deployment_context is None:
            self._deployment_context = self._detect_deployment_context()
        return self._deployment_context

    def discover_agent_paths(
        self, agents_dir: Optional[Path] = None, framework_path: Optional[Path] = None
    ) -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
        """
        Discover agent directories based on priority.

        Args:
            agents_dir: Custom agents directory override
            framework_path: Framework path to search in

        Returns:
            Tuple of (agents_dir, templates_dir, main_dir)
        """
        discovered_agents_dir = None
        templates_dir = None
        main_dir = None

        if agents_dir and agents_dir.exists():
            discovered_agents_dir = agents_dir
            self.logger.debug(f"Using custom agents directory: {discovered_agents_dir}")
        elif framework_path and framework_path != Path("__PACKAGED__"):
            # Prioritize templates directory over main agents directory
            templates_dir = (
                framework_path / "src" / "claude_mpm" / "agents" / "templates"
            )
            main_dir = framework_path / "src" / "claude_mpm" / "agents"

            if templates_dir.exists() and any(templates_dir.glob("*.md")):
                discovered_agents_dir = templates_dir
                self.logger.info(
                    f"Using agents from templates directory: {discovered_agents_dir}"
                )
            elif main_dir.exists() and any(main_dir.glob("*.md")):
                discovered_agents_dir = main_dir
                self.logger.info(
                    f"Using agents from main directory: {discovered_agents_dir}"
                )

        return discovered_agents_dir, templates_dir, main_dir

    def get_instruction_file_paths(self) -> Dict[str, Optional[Path]]:
        """
        Get paths for instruction files with precedence.

        Returns:
            Dictionary mapping instruction type to path:
            - "project": Project-specific INSTRUCTIONS.md
            - "user": User-specific INSTRUCTIONS.md
            - "system": System-wide INSTRUCTIONS.md
        """
        paths = {"project": None, "user": None, "system": None}

        # Project-specific instructions
        project_path = self._get_working_dir() / ".claude-mpm" / "INSTRUCTIONS.md"
        if project_path.exists():
            paths["project"] = project_path

        # User-specific instructions
        user_path = Path.home() / ".claude-mpm" / "INSTRUCTIONS.md"
        if user_path.exists():
            paths["user"] = user_path

        # System-wide instructions (if framework is detected)
        framework_path = self.detect_framework_path()
        if framework_path and framework_path != Path("__PACKAGED__"):
            system_path = (
                framework_path / "src" / "claude_mpm" / "agents" / "INSTRUCTIONS.md"
            )
            if system_path.exists():
                paths["system"] = system_path

        return paths

    # Private helper methods

    def _detect_via_unified_paths(self) -> Optional[Path]:
        """Detect framework path using unified path management."""
        try:
            # Import here to avoid circular dependencies
            from ...core.unified_paths import (
                DeploymentContext as UnifiedContext,
                get_path_manager,
            )

            path_manager = get_path_manager()
            deployment_context = path_manager._deployment_context

            # Map unified context to our context
            context_map = {
                UnifiedContext.PIP_INSTALL: DeploymentContext.PIP_INSTALL,
                UnifiedContext.PIPX_INSTALL: DeploymentContext.PIPX_INSTALL,
                UnifiedContext.SYSTEM_PACKAGE: DeploymentContext.SYSTEM_PACKAGE,
                UnifiedContext.DEVELOPMENT: DeploymentContext.DEVELOPMENT,
                UnifiedContext.EDITABLE_INSTALL: DeploymentContext.EDITABLE_INSTALL,
            }

            if deployment_context in context_map:
                self._deployment_context = context_map[deployment_context]

            # Check if we're in a packaged installation
            if deployment_context in [
                UnifiedContext.PIP_INSTALL,
                UnifiedContext.PIPX_INSTALL,
                UnifiedContext.SYSTEM_PACKAGE,
            ]:
                self.logger.info(
                    f"Running from packaged installation (context: {deployment_context})"
                )
                return Path("__PACKAGED__")

            if deployment_context == UnifiedContext.DEVELOPMENT:
                # Development mode - use framework root
                framework_root = path_manager.framework_root
                if (framework_root / "src" / "claude_mpm" / "agents").exists():
                    self.logger.info(
                        f"Using claude-mpm development installation at: {framework_root}"
                    )
                    return framework_root

            elif deployment_context == UnifiedContext.EDITABLE_INSTALL:
                # Editable install - similar to development
                framework_root = path_manager.framework_root
                if (framework_root / "src" / "claude_mpm" / "agents").exists():
                    self.logger.info(
                        f"Using claude-mpm editable installation at: {framework_root}"
                    )
                    return framework_root

        except Exception as e:
            self.logger.warning(
                f"Failed to use unified path manager for framework detection: {e}"
            )

        return None

    def _detect_via_package(self) -> Optional[Path]:
        """Detect framework via package installation."""
        try:
            import claude_mpm

            package_file = Path(claude_mpm.__file__)

            # For packaged installations, we don't need a framework path
            # since we'll use importlib.resources to load files
            if "site-packages" in str(package_file) or "dist-packages" in str(
                package_file
            ):
                self.logger.info(
                    f"Running from packaged installation at: {package_file.parent}"
                )
                self._deployment_context = DeploymentContext.PIP_INSTALL
                return Path("__PACKAGED__")
        except ImportError:
            pass

        return None

    def _detect_development_mode(self) -> Optional[Path]:
        """Detect if running in development mode."""
        current_file = Path(__file__)

        if "claude-mpm" in str(current_file):
            # We're running from claude-mpm, use its agents
            for parent in current_file.parents:
                if parent.name == "claude-mpm":
                    if (parent / "src" / "claude_mpm" / "agents").exists():
                        self.logger.info(f"Using claude-mpm at: {parent}")
                        self._deployment_context = DeploymentContext.DEVELOPMENT
                        return parent
                    break

        return None

    def _check_common_locations(self) -> Optional[Path]:
        """Check common locations for claude-mpm."""
        candidates = [
            # Current directory (if we're already in claude-mpm)
            self._get_working_dir(),
            # Development location
            Path.home() / "Projects" / "claude-mpm",
            # Current directory subdirectory
            self._get_working_dir() / "claude-mpm",
        ]

        for candidate in candidates:
            if (
                candidate
                and candidate.exists()
                and (candidate / "src" / "claude_mpm" / "agents").exists()
            ):
                # Found claude-mpm agents directory
                self.logger.info(f"Found claude-mpm at: {candidate}")
                return candidate

        return None

    def _detect_npm_global(self) -> Optional[Path]:
        """Detect npm global installation path."""
        try:
            result = subprocess.run(
                ["npm", "root", "-g"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                npm_root = Path(result.stdout.strip())
                npm_path = npm_root / "@bobmatnyc" / "claude-multiagent-pm"
                if npm_path.exists():
                    return npm_path
        except (subprocess.SubprocessError, OSError, FileNotFoundError):
            pass

        return None

    def _detect_deployment_context(self) -> DeploymentContext:
        """Detect the current deployment context."""
        # If already detected via framework path detection
        if self._deployment_context:
            return self._deployment_context

        # Try to detect based on current environment
        try:
            import claude_mpm

            package_file = Path(claude_mpm.__file__)
            package_str = str(package_file)

            # Check for pipx first (more specific)
            if ".local" in package_str and "pipx" in package_str:
                return DeploymentContext.PIPX_INSTALL
            if "dist-packages" in package_str:
                return DeploymentContext.SYSTEM_PACKAGE
            if "site-packages" in package_str:
                return DeploymentContext.PIP_INSTALL

        except ImportError:
            pass

        # Check if we're in development
        if (self._get_working_dir() / "pyproject.toml").exists():
            return DeploymentContext.DEVELOPMENT

        return DeploymentContext.UNKNOWN

    def _cache_framework_path(self, path: Path) -> None:
        """Cache the framework path."""
        self._framework_path = path

        # Cache internally
        cache_value = str(path) if path != Path("__PACKAGED__") else "__PACKAGED__"
        self._path_cache["framework_path"] = cache_value
