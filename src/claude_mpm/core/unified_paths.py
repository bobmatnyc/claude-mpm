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

import os
import sys
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

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
    @lru_cache(maxsize=1)
    def detect_deployment_context() -> DeploymentContext:
        """Detect the current deployment context."""
        try:
            import claude_mpm
            module_path = Path(claude_mpm.__file__).parent
            
            # Check for development mode
            if (module_path.parent / "src").exists():
                return DeploymentContext.DEVELOPMENT
            
            # Check for editable install
            if "site-packages" in str(module_path) and (module_path.parent.parent / "src").exists():
                return DeploymentContext.EDITABLE_INSTALL
            
            # Check for pipx install
            if "pipx" in str(module_path):
                return DeploymentContext.PIPX_INSTALL
            
            # Check for system package
            if "dist-packages" in str(module_path):
                return DeploymentContext.SYSTEM_PACKAGE
            
            # Default to pip install
            return DeploymentContext.PIP_INSTALL
            
        except ImportError:
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
            ".git", "pyproject.toml", "package.json", "Cargo.toml", 
            "go.mod", "pom.xml", "build.gradle", self.CONFIG_DIR_NAME
        ]
        self._initialized = True
        
        logger.debug(f"UnifiedPathManager initialized with context: {self._deployment_context}")
    
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
            
            if self._deployment_context == DeploymentContext.DEVELOPMENT:
                # Development: go up to project root
                current = module_path
                while current != current.parent:
                    if (current / "src" / "claude_mpm").exists():
                        return current
                    current = current.parent
            
            # For installed packages, the module path is the framework root
            return module_path.parent if module_path.name == "claude_mpm" else module_path
            
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
        elif scope == "project":
            return self.project_root / self.CONFIG_DIR_NAME
        elif scope == "framework":
            return self.framework_root / self.CONFIG_DIR_NAME
        else:
            raise ValueError(f"Invalid scope: {scope}. Must be 'user', 'project', or 'framework'")
    
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
        elif scope == "project":
            return self.get_project_config_dir() / "agents"
        elif scope == "framework":
            if self._deployment_context == DeploymentContext.DEVELOPMENT:
                return self.framework_root / "src" / "claude_mpm" / "agents"
            else:
                return self.package_root / "agents"
        else:
            raise ValueError(f"Invalid scope: {scope}. Must be 'user', 'project', or 'framework'")
    
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
        if self._deployment_context == DeploymentContext.DEVELOPMENT:
            return self.framework_root / "scripts"
        else:
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

    def find_file_upwards(self, filename: str, start_path: Optional[Path] = None) -> Optional[Path]:
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

    def get_relative_to_root(self, path: Union[str, Path], root_type: str = "project") -> Path:
        """Get a path relative to a specific root."""
        if root_type == "project":
            root = self.project_root
        elif root_type == "framework":
            root = self.framework_root
        else:
            raise ValueError(f"Invalid root_type: {root_type}. Must be 'project' or 'framework'")

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
            if hasattr(type(self).framework_root, 'fget') and hasattr(type(self).framework_root.fget, 'cache_clear'):
                type(self).framework_root.fget.cache_clear()
            if hasattr(type(self).project_root, 'fget') and hasattr(type(self).project_root.fget, 'cache_clear'):
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

def find_file_upwards(filename: str, start_path: Optional[Path] = None) -> Optional[Path]:
    """Search for a file by traversing up the directory tree."""
    return get_path_manager().find_file_upwards(filename, start_path)

def get_package_resource_path(resource_path: str) -> Path:
    """Get the path to a resource within the claude_mpm package."""
    return get_path_manager().get_package_resource_path(resource_path)


# ============================================================================
# Export All Public Symbols
# ============================================================================

__all__ = [
    "UnifiedPathManager",
    "PathType",
    "DeploymentContext",
    "PathContext",
    "get_path_manager",
    "get_project_root",
    "get_framework_root",
    "get_package_root",
    "get_scripts_dir",
    "get_agents_dir",
    "get_config_dir",
    "find_file_upwards",
    "get_package_resource_path",
]
