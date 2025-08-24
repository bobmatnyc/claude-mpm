#!/usr/bin/env python3
"""
Unified Path Management System for Claude MPM
==============================================

This module consolidates all path management functionality from the duplicate modules:
- config/paths.py (ClaudeMPMPaths)
- utils/paths.py (get_path_manager())
- deployment_paths.py (get_path_manager())
- core/config_paths.py (get_path_manager())

Design Principles:
- Single source of truth for all path operations
- Consistent API across all path types
- Robust deployment scenario handling
- Efficient caching with cache invalidation
- Clear separation of concerns
- Backward compatibility during migration

Architecture:
- UnifiedPathManager: Main singleton class
- PathType enum: Categorizes different path types
- PathContext: Handles deployment context detection
- Cached properties with smart invalidation
"""

import logging
import os
import sys
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


class PathType(Enum):
    """Enumeration of different path types for categorization."""

    PROJECT = "project"
    FRAMEWORK = "framework"
    USER = "user"
    SYSTEM = "system"
    CONFIG = "config"
    AGENTS = "agents"
    TEMPLATES = "templates"
    SCRIPTS = "scripts"
    STATIC = "static"
    LOGS = "logs"
    CACHE = "cache"


class DeploymentContext(Enum):
    """Enumeration of deployment contexts."""

    DEVELOPMENT = "development"
    EDITABLE_INSTALL = "editable_install"
    PIP_INSTALL = "pip_install"
    PIPX_INSTALL = "pipx_install"
    SYSTEM_PACKAGE = "system_package"


class PathContext:
    """Handles deployment context detection and path resolution."""

    @staticmethod
    def _is_editable_install() -> bool:
        """Check if the current installation is editable (development mode).

        This checks for various indicators of an editable/development installation:
        - Presence of pyproject.toml in parent directories
        - .pth files pointing to the source directory
        - Direct source installation (src/ directory structure)
        - Current working directory is within a development project
        """
        try:
            import claude_mpm

            module_path = Path(claude_mpm.__file__).parent

            # Check if we're in a src/ directory structure with pyproject.toml
            current = module_path
            for _ in range(5):  # Check up to 5 levels up
                if (current / "pyproject.toml").exists():
                    # Found pyproject.toml, check if this looks like a development setup
                    if (current / "src" / "claude_mpm").exists():
                        logger.debug(f"Found development installation at {current}")
                        return True
                if current == current.parent:
                    break
                current = current.parent

            # Additional check: If we're running from within a claude-mpm development directory
            # This handles the case where pipx claude-mpm is invoked from within the dev directory
            cwd = Path.cwd()
            current = cwd
            for _ in range(5):  # Check up to 5 levels up from current directory
                if (current / "pyproject.toml").exists() and (
                    current / "src" / "claude_mpm"
                ).exists():
                    # Check if this is the claude-mpm project
                    try:
                        pyproject_content = (current / "pyproject.toml").read_text()
                        if (
                            "claude-mpm" in pyproject_content
                            and "claude_mpm" in pyproject_content
                        ):
                            logger.debug(
                                f"Running from within claude-mpm development directory: {current}"
                            )
                            # Verify this is a development setup by checking for key files
                            if (current / "scripts" / "claude-mpm").exists():
                                return True
                    except Exception:
                        pass
                if current == current.parent:
                    break
                current = current.parent

            # Check for .pth files indicating editable install
            try:
                import site

                for site_dir in site.getsitepackages():
                    site_path = Path(site_dir)
                    if site_path.exists():
                        # Check for .pth files
                        for pth_file in site_path.glob("*.pth"):
                            try:
                                content = pth_file.read_text()
                                # Check if the .pth file points to our module's parent
                                if (
                                    str(module_path.parent) in content
                                    or str(module_path) in content
                                ):
                                    logger.debug(
                                        f"Found editable install via .pth file: {pth_file}"
                                    )
                                    return True
                            except Exception:
                                continue

                        # Check for egg-link files
                        for egg_link in site_path.glob("*egg-link"):
                            if "claude" in egg_link.name.lower():
                                try:
                                    content = egg_link.read_text()
                                    if (
                                        str(module_path.parent) in content
                                        or str(module_path) in content
                                    ):
                                        logger.debug(
                                            f"Found editable install via egg-link: {egg_link}"
                                        )
                                        return True
                                except Exception:
                                    continue
            except ImportError:
                pass

        except Exception as e:
            logger.debug(f"Error checking for editable install: {e}")

        return False

    @staticmethod
    @lru_cache(maxsize=1)
    def detect_deployment_context() -> DeploymentContext:
        """Detect the current deployment context.

        Priority order:
        1. Environment variable override (CLAUDE_MPM_DEV_MODE)
        2. Current working directory is a claude-mpm development project
        3. Editable installation detection
        4. Path-based detection (development, pipx, system, pip)
        """
        # Check for environment variable override
        if os.environ.get("CLAUDE_MPM_DEV_MODE", "").lower() in ("1", "true", "yes"):
            logger.info(
                "Development mode forced via CLAUDE_MPM_DEV_MODE environment variable"
            )
            return DeploymentContext.DEVELOPMENT

        # Check if current working directory is a claude-mpm development project
        # This handles the case where pipx claude-mpm is run from within the dev directory
        cwd = Path.cwd()
        current = cwd
        for _ in range(5):  # Check up to 5 levels up from current directory
            if (current / "pyproject.toml").exists() and (
                current / "src" / "claude_mpm"
            ).exists():
                # Check if this is the claude-mpm project
                try:
                    pyproject_content = (current / "pyproject.toml").read_text()
                    if (
                        'name = "claude-mpm"' in pyproject_content
                        or '"claude-mpm"' in pyproject_content
                    ):
                        logger.info(
                            f"Detected claude-mpm development directory at {current}"
                        )
                        logger.info(
                            "Using development mode for local source preference"
                        )
                        return DeploymentContext.DEVELOPMENT
                except Exception:
                    pass
            if current == current.parent:
                break
            current = current.parent

        try:
            import claude_mpm

            module_path = Path(claude_mpm.__file__).parent

            # First check if this is an editable install, regardless of path
            # This is important for cases where pipx points to a development installation
            if PathContext._is_editable_install():
                logger.info("Detected editable/development installation")
                # Check if we should use development paths
                # This could be because we're in a src/ directory or running from dev directory
                if module_path.parent.name == "src":
                    return DeploymentContext.DEVELOPMENT
                if "pipx" in str(module_path):
                    # Running via pipx but from within a development directory
                    # Use development mode to prefer local source over pipx installation
                    cwd = Path.cwd()
                    current = cwd
                    for _ in range(5):
                        if (current / "src" / "claude_mpm").exists() and (
                            current / "pyproject.toml"
                        ).exists():
                            logger.info(
                                "Running pipx from development directory, using development mode"
                            )
                            return DeploymentContext.DEVELOPMENT
                        if current == current.parent:
                            break
                        current = current.parent
                    return DeploymentContext.EDITABLE_INSTALL
                return DeploymentContext.EDITABLE_INSTALL

            # Check for development mode based on directory structure
            # module_path is typically /path/to/project/src/claude_mpm
            if (
                module_path.parent.name == "src"
                and (module_path.parent.parent / "src" / "claude_mpm").exists()
            ):
                logger.info(
                    f"Detected development mode via directory structure at {module_path}"
                )
                return DeploymentContext.DEVELOPMENT

            # Check for pipx install
            if "pipx" in str(module_path):
                logger.info(f"Detected pipx installation at {module_path}")
                return DeploymentContext.PIPX_INSTALL

            # Check for system package
            if "dist-packages" in str(module_path):
                logger.info(f"Detected system package installation at {module_path}")
                return DeploymentContext.SYSTEM_PACKAGE

            # Check for site-packages (could be pip or editable)
            if "site-packages" in str(module_path):
                # Already checked for editable above, so this is a regular pip install
                logger.info(f"Detected pip installation at {module_path}")
                return DeploymentContext.PIP_INSTALL

            # Default to pip install
            logger.info(f"Defaulting to pip installation for {module_path}")
            return DeploymentContext.PIP_INSTALL

        except ImportError:
            logger.info(
                "ImportError during context detection, defaulting to development"
            )
            return DeploymentContext.DEVELOPMENT


class UnifiedPathManager:
    """
    Unified path management system that consolidates all path-related functionality.

    This class provides a single, authoritative interface for all path operations
    in Claude MPM, replacing the multiple duplicate path management modules.
    """

    _instance: Optional["UnifiedPathManager"] = None
    _cache_invalidated: bool = False

    # Configuration constants
    CONFIG_DIR_NAME = ".claude-mpm"
    LEGACY_CONFIG_DIR_NAME = ".claude-pm"  # For migration support

    def __new__(cls) -> "UnifiedPathManager":
        """Singleton pattern to ensure single instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the path manager."""
        if self._initialized:
            return

        self._deployment_context = PathContext.detect_deployment_context()
        self._project_markers = [
            ".git",
            "pyproject.toml",
            "package.json",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            self.CONFIG_DIR_NAME,
        ]
        self._initialized = True

        logger.info(
            f"UnifiedPathManager initialized with context: {self._deployment_context.value}"
        )

    # ========================================================================
    # Core Path Resolution Methods
    # ========================================================================

    @property
    @lru_cache(maxsize=1)
    def framework_root(self) -> Path:
        """Get the framework root directory."""
        try:
            import claude_mpm

            module_path = Path(claude_mpm.__file__).parent

            if self._deployment_context in (
                DeploymentContext.DEVELOPMENT,
                DeploymentContext.EDITABLE_INSTALL,
            ):
                # For development mode, first check if we're running from within a dev directory
                # This handles the case where pipx is invoked from a development directory
                cwd = Path.cwd()
                current = cwd
                for _ in range(5):
                    if (current / "src" / "claude_mpm").exists() and (
                        current / "pyproject.toml"
                    ).exists():
                        # Verify this is the claude-mpm project
                        try:
                            pyproject_content = (current / "pyproject.toml").read_text()
                            if "claude-mpm" in pyproject_content:
                                logger.debug(
                                    f"Found framework root via cwd at {current}"
                                )
                                return current
                        except Exception:
                            pass
                    if current == current.parent:
                        break
                    current = current.parent

                # Development or editable install: go up to project root from module
                current = module_path
                while current != current.parent:
                    if (current / "src" / "claude_mpm").exists() and (
                        current / "pyproject.toml"
                    ).exists():
                        logger.debug(f"Found framework root at {current}")
                        return current
                    current = current.parent

                # Secondary check: Look for pyproject.toml without src structure
                current = module_path
                while current != current.parent:
                    if (current / "pyproject.toml").exists():
                        logger.debug(f"Found framework root (no src) at {current}")
                        return current
                    current = current.parent

            # For installed packages, the module path is the framework root
            return (
                module_path.parent if module_path.name == "claude_mpm" else module_path
            )

        except ImportError:
            # Fallback: search from current file location
            current = Path(__file__).parent
            while current != current.parent:
                if (current / "src" / "claude_mpm").exists():
                    return current
                current = current.parent

            raise FileNotFoundError("Could not determine framework root")

    @property
    @lru_cache(maxsize=1)
    def project_root(self) -> Path:
        """Get the current project root directory."""
        current = Path.cwd()
        while current != current.parent:
            for marker in self._project_markers:
                if (current / marker).exists():
                    logger.debug(f"Found project root at {current} via {marker}")
                    return current
            current = current.parent

        # Fallback to current directory
        logger.warning("Could not find project root, using current directory")
        return Path.cwd()

    @property
    def package_root(self) -> Path:
        """Get the claude_mpm package root directory."""
        if self._deployment_context in (
            DeploymentContext.DEVELOPMENT,
            DeploymentContext.EDITABLE_INSTALL,
        ):
            # In development mode, always use the source directory
            package_path = self.framework_root / "src" / "claude_mpm"
            if package_path.exists():
                return package_path

        try:
            import claude_mpm

            return Path(claude_mpm.__file__).parent
        except ImportError:
            return self.framework_root / "src" / "claude_mpm"

    # ========================================================================
    # Configuration Paths
    # ========================================================================

    def get_config_dir(self, scope: str = "project") -> Path:
        """Get configuration directory for specified scope."""
        if scope == "user":
            return Path.home() / self.CONFIG_DIR_NAME
        if scope == "project":
            return self.project_root / self.CONFIG_DIR_NAME
        if scope == "framework":
            return self.framework_root / self.CONFIG_DIR_NAME
        raise ValueError(
            f"Invalid scope: {scope}. Must be 'user', 'project', or 'framework'"
        )

    def get_user_config_dir(self) -> Path:
        """Get the user-level configuration directory."""
        return Path.home() / self.CONFIG_DIR_NAME

    def get_project_config_dir(self, project_root: Optional[Path] = None) -> Path:
        """Get the project-level configuration directory."""
        root = project_root or self.project_root
        return root / self.CONFIG_DIR_NAME

    # ========================================================================
    # Agent Paths
    # ========================================================================

    def get_agents_dir(self, scope: str = "framework") -> Path:
        """Get agents directory for specified scope."""
        if scope == "user":
            return self.get_user_config_dir() / "agents"
        if scope == "project":
            return self.get_project_config_dir() / "agents"
        if scope == "framework":
            if self._deployment_context in (
                DeploymentContext.DEVELOPMENT,
                DeploymentContext.EDITABLE_INSTALL,
            ):
                return self.framework_root / "src" / "claude_mpm" / "agents"
            return self.package_root / "agents"
        raise ValueError(
            f"Invalid scope: {scope}. Must be 'user', 'project', or 'framework'"
        )

    def get_user_agents_dir(self) -> Path:
        """Get the user-level agents directory."""
        return self.get_user_config_dir() / "agents"

    def get_project_agents_dir(self, project_root: Optional[Path] = None) -> Path:
        """Get the project-level agents directory."""
        return self.get_project_config_dir(project_root) / "agents"

    def get_system_agents_dir(self) -> Path:
        """Get the system-level agents directory."""
        return self.get_agents_dir("framework")

    def get_templates_dir(self) -> Path:
        """Get the agent templates directory."""
        return self.get_agents_dir("framework") / "templates"

    # ========================================================================
    # Resource and Static Paths
    # ========================================================================

    def get_scripts_dir(self) -> Path:
        """Get the scripts directory."""
        if self._deployment_context in (
            DeploymentContext.DEVELOPMENT,
            DeploymentContext.EDITABLE_INSTALL,
        ):
            return self.framework_root / "scripts"
        return self.package_root / "scripts"

    def get_static_dir(self) -> Path:
        """Get the static files directory."""
        return self.package_root / "dashboard" / "static"

    def get_templates_web_dir(self) -> Path:
        """Get the web templates directory."""
        return self.package_root / "dashboard" / "templates"

    # ========================================================================
    # Utility and Working Paths
    # ========================================================================

    def get_logs_dir(self, scope: str = "project") -> Path:
        """Get logs directory for specified scope."""
        base_dir = self.get_config_dir(scope)
        return base_dir / "logs"

    def get_cache_dir(self, scope: str = "user") -> Path:
        """Get cache directory for specified scope."""
        base_dir = self.get_config_dir(scope)
        return base_dir / "cache"

    def get_backups_dir(self, scope: str = "user") -> Path:
        """Get backups directory for specified scope."""
        base_dir = self.get_config_dir(scope)
        return base_dir / "backups"

    def get_memories_dir(self, scope: str = "project") -> Path:
        """Get memories directory for specified scope."""
        base_dir = self.get_config_dir(scope)
        return base_dir / "memories"

    # ========================================================================
    # File Path Resolution
    # ========================================================================

    def get_resource_path(self, resource_type: str, filename: str) -> Path:
        """Get path to a resource file."""
        resource_dirs = {
            "scripts": self.get_scripts_dir(),
            "templates": self.get_templates_dir(),
            "static": self.get_static_dir(),
            "agents": self.get_agents_dir("framework"),
            "web_templates": self.get_templates_web_dir(),
        }

        base_dir = resource_dirs.get(resource_type, self.package_root)
        return base_dir / filename

    def find_file_upwards(
        self, filename: str, start_path: Optional[Path] = None
    ) -> Optional[Path]:
        """Search for a file by traversing up the directory tree."""
        current = start_path or Path.cwd()

        while current != current.parent:
            candidate = current / filename
            if candidate.exists():
                return candidate
            current = current.parent

        return None

    def get_package_resource_path(self, resource_path: str) -> Path:
        """Get the path to a resource within the claude_mpm package."""
        # Try using importlib.resources for proper package resource access
        try:
            from importlib import resources

            parts = resource_path.split("/")
            if len(parts) == 1:
                with resources.path("claude_mpm", parts[0]) as p:
                    if p.exists():
                        return p
            else:
                # For nested paths, navigate step by step
                package = "claude_mpm"
                for part in parts[:-1]:
                    package = f"{package}.{part}"
                with resources.path(package, parts[-1]) as p:
                    if p.exists():
                        return p
        except (ImportError, ModuleNotFoundError, TypeError, AttributeError):
            # Fall back to file system detection
            pass

        # Fallback: Use package root
        resource = self.package_root / resource_path
        if resource.exists():
            return resource

        raise FileNotFoundError(f"Resource not found: {resource_path}")

    # ========================================================================
    # Path Validation and Utilities
    # ========================================================================

    def ensure_directory(self, path: Path) -> Path:
        """Ensure a directory exists, creating it if necessary."""
        path.mkdir(parents=True, exist_ok=True)
        return path

    def validate_not_legacy(self, path: Path) -> bool:
        """Check if a path contains the legacy configuration directory name."""
        return self.LEGACY_CONFIG_DIR_NAME not in str(path)

    def get_relative_to_root(
        self, path: Union[str, Path], root_type: str = "project"
    ) -> Path:
        """Get a path relative to a specific root."""
        if root_type == "project":
            root = self.project_root
        elif root_type == "framework":
            root = self.framework_root
        else:
            raise ValueError(
                f"Invalid root_type: {root_type}. Must be 'project' or 'framework'"
            )

        return root / path

    def resolve_import_path(self, module_path: str) -> Path:
        """Resolve a module import path to a file path."""
        parts = module_path.split(".")
        if parts[0] == "claude_mpm":
            parts = parts[1:]  # Remove package name

        return self.package_root.joinpath(*parts).with_suffix(".py")

    # ========================================================================
    # Cache Management
    # ========================================================================

    def clear_cache(self):
        """Clear all cached path lookups."""
        # Clear lru_cache instances
        try:
            # Clear property caches if they exist
            if hasattr(type(self).framework_root, "fget") and hasattr(
                type(self).framework_root.fget, "cache_clear"
            ):
                type(self).framework_root.fget.cache_clear()
            if hasattr(type(self).project_root, "fget") and hasattr(
                type(self).project_root.fget, "cache_clear"
            ):
                type(self).project_root.fget.cache_clear()
        except AttributeError:
            # Properties might not have cache_clear if not using lru_cache
            pass

        # Clear static method cache
        PathContext.detect_deployment_context.cache_clear()

        logger.debug("Cleared all UnifiedPathManager caches")

    def invalidate_cache(self):
        """Mark cache as invalidated for next access."""
        self._cache_invalidated = True
        self.clear_cache()

    # ========================================================================
    # Legacy Compatibility Methods
    # ========================================================================

    def get_version(self) -> str:
        """Get the project version."""
        version_candidates = [
            self.framework_root / "VERSION",
            self.package_root / "VERSION",
            self.project_root / "VERSION",
        ]

        for version_file in version_candidates:
            if version_file.exists():
                return version_file.read_text().strip()

        # Fallback to package metadata
        try:
            import claude_mpm

            return getattr(claude_mpm, "__version__", "unknown")
        except (ImportError, AttributeError):
            return "unknown"

    def ensure_src_in_path(self):
        """Ensure src directory is in Python path."""
        src_dir = self.framework_root / "src"
        if src_dir.exists() and str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

    def get_executable_path(self) -> Optional[Path]:
        """Get the path to the claude-mpm executable for the current deployment context.

        This method provides deployment-context-aware executable path detection,
        particularly useful for MCP server configuration.

        Returns:
            Path to executable or None if not found
        """
        import shutil

        # Try standard which first
        which_result = shutil.which("claude-mpm")
        if which_result:
            return Path(which_result)

        # Enhanced detection based on deployment context
        if self._deployment_context == DeploymentContext.PIPX_INSTALL:
            return self._find_pipx_executable()
        if self._deployment_context in (
            DeploymentContext.DEVELOPMENT,
            DeploymentContext.EDITABLE_INSTALL,
        ):
            return self._find_development_executable()
        if self._deployment_context == DeploymentContext.PIP_INSTALL:
            return self._find_pip_executable()

        return None

    def _find_pipx_executable(self) -> Optional[Path]:
        """Find claude-mpm executable in pipx installation."""
        try:
            import claude_mpm

            module_path = Path(claude_mpm.__file__).parent

            if "pipx" not in str(module_path):
                return None

            # Common pipx executable locations
            home = Path.home()
            pipx_paths = [
                home / ".local" / "bin" / "claude-mpm",
                home
                / ".local"
                / "share"
                / "pipx"
                / "venvs"
                / "claude-mpm"
                / "bin"
                / "claude-mpm",
            ]

            # Windows paths
            if sys.platform == "win32":
                pipx_paths.extend(
                    [
                        home / "AppData" / "Local" / "pipx" / "bin" / "claude-mpm.exe",
                        home / ".local" / "bin" / "claude-mpm.exe",
                    ]
                )

            for path in pipx_paths:
                if path.exists():
                    logger.debug(f"Found pipx executable: {path}")
                    return path

            # Try to derive from module path
            # Navigate up from module to find venv, then to bin
            venv_path = module_path
            for _ in range(5):  # Prevent infinite loops
                if (
                    venv_path.name == "claude-mpm"
                    and (venv_path / "pyvenv.cfg").exists()
                ):
                    # Found the venv directory
                    bin_dir = venv_path / (
                        "Scripts" if sys.platform == "win32" else "bin"
                    )
                    exe_name = (
                        "claude-mpm.exe" if sys.platform == "win32" else "claude-mpm"
                    )
                    exe_path = bin_dir / exe_name

                    if exe_path.exists():
                        logger.debug(
                            f"Found pipx executable via module path: {exe_path}"
                        )
                        return exe_path
                    break

                if venv_path == venv_path.parent:
                    break
                venv_path = venv_path.parent

        except Exception as e:
            logger.debug(f"Error finding pipx executable: {e}")

        return None

    def _find_development_executable(self) -> Optional[Path]:
        """Find claude-mpm executable in development installation."""
        # For development, prefer the script in the project
        scripts_dir = self.get_scripts_dir()
        dev_executable = scripts_dir / "claude-mpm"

        if dev_executable.exists():
            return dev_executable

        # Check if we're in a development venv
        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            venv_bin = Path(sys.prefix) / (
                "Scripts" if sys.platform == "win32" else "bin"
            )
            venv_executable = venv_bin / "claude-mpm"
            if venv_executable.exists():
                return venv_executable

        return None

    def _find_pip_executable(self) -> Optional[Path]:
        """Find claude-mpm executable in pip installation."""
        # For pip installs, check the current Python environment
        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            # In a virtual environment
            venv_bin = Path(sys.prefix) / (
                "Scripts" if sys.platform == "win32" else "bin"
            )
            venv_executable = venv_bin / "claude-mpm"
            if venv_executable.exists():
                return venv_executable

        # Check system-wide installation
        try:
            import site

            for site_dir in site.getsitepackages():
                # Look for installed scripts
                site_path = Path(site_dir)
                scripts_dir = site_path.parent / (
                    "Scripts" if sys.platform == "win32" else "bin"
                )
                if scripts_dir.exists():
                    exe_path = scripts_dir / "claude-mpm"
                    if exe_path.exists():
                        return exe_path
        except Exception as e:
            logger.debug(f"Error finding pip executable: {e}")

        return None


# ============================================================================
# Singleton Instance and Convenience Functions
# ============================================================================

# Global singleton instance
_path_manager: Optional[UnifiedPathManager] = None


def get_path_manager() -> UnifiedPathManager:
    """Get the global UnifiedPathManager instance."""
    global _path_manager
    if _path_manager is None:
        _path_manager = UnifiedPathManager()
    return _path_manager


# Convenience functions for backward compatibility
def get_project_root() -> Path:
    """Get the current project root directory."""
    return get_path_manager().project_root


def get_framework_root() -> Path:
    """Get the framework root directory."""
    return get_path_manager().framework_root


def get_package_root() -> Path:
    """Get the claude_mpm package root directory."""
    return get_path_manager().package_root


def get_scripts_dir() -> Path:
    """Get the scripts directory."""
    return get_path_manager().get_scripts_dir()


def get_agents_dir() -> Path:
    """Get the framework agents directory."""
    return get_path_manager().get_agents_dir("framework")


def get_config_dir(scope: str = "project") -> Path:
    """Get configuration directory for specified scope."""
    return get_path_manager().get_config_dir(scope)


def find_file_upwards(
    filename: str, start_path: Optional[Path] = None
) -> Optional[Path]:
    """Search for a file by traversing up the directory tree."""
    return get_path_manager().find_file_upwards(filename, start_path)


def get_package_resource_path(resource_path: str) -> Path:
    """Get the path to a resource within the claude_mpm package."""
    return get_path_manager().get_package_resource_path(resource_path)


def get_executable_path() -> Optional[Path]:
    """Get the claude-mpm executable path for the current deployment context."""
    return get_path_manager().get_executable_path()


# ============================================================================
# Export All Public Symbols
# ============================================================================

__all__ = [
    "DeploymentContext",
    "PathContext",
    "PathType",
    "UnifiedPathManager",
    "find_file_upwards",
    "get_agents_dir",
    "get_config_dir",
    "get_executable_path",
    "get_framework_root",
    "get_package_resource_path",
    "get_package_root",
    "get_path_manager",
    "get_project_root",
    "get_scripts_dir",
]
