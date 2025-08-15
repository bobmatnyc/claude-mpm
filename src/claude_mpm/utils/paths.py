"""Path resolution utilities for Claude MPM.

This module provides centralized path discovery and resolution logic
to avoid duplication across the codebase.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union, List
from functools import lru_cache
import logging

from claude_mpm.core.config_paths import ConfigPaths

logger = logging.getLogger(__name__)


class PathResolver:
    """Centralized path resolution for Claude MPM.
    
    This class consolidates all path discovery logic to avoid duplication
    across different modules. It handles various scenarios including:
    - Running from different directories
    - Installed vs development mode
    - Missing directories
    
    All methods use caching to improve performance for repeated lookups.
    """
    
    @classmethod
    @lru_cache(maxsize=1)
    def get_framework_root(cls) -> Path:
        """Find the framework root directory.
        
        This method searches for the framework root by looking for marker files
        like pyproject.toml or the claude_mpm package directory.
        
        Returns:
            Path: The framework root directory
            
        Raises:
            FileNotFoundError: If framework root cannot be determined
        """
        # First, try to find via the module location
        try:
            import claude_mpm
            module_path = Path(claude_mpm.__file__).parent
            
            # Check if we're in a development environment (has src/ directory)
            if module_path.parent.name == 'src':
                # Development structure: project_root/src/claude_mpm/
                return module_path.parent.parent
            
            # Check if we're in an installed environment (site-packages)
            # In this case, the module itself IS the framework root for resources
            # No src/ directory exists in installed packages
            return module_path
            
        except ImportError:
            pass
        
        # Fallback: search upward for pyproject.toml
        current = Path.cwd()
        while current != current.parent:
            if (current / 'pyproject.toml').exists():
                # Verify this is our project
                if (current / 'src' / 'claude_mpm').exists():
                    return current
            current = current.parent
        
        raise FileNotFoundError(
            "Could not determine framework root. Please run from within "
            "the claude-mpm project or ensure it's properly installed."
        )
    
    @classmethod
    @lru_cache(maxsize=1)
    def get_agents_dir(cls) -> Path:
        """Get the agents directory path.
        
        Returns:
            Path: The agents directory within the framework
            
        Raises:
            FileNotFoundError: If agents directory doesn't exist
        """
        # Try using importlib.resources first (Python 3.9+)
        try:
            if sys.version_info >= (3, 9):
                from importlib.resources import files
                agents_path = files('claude_mpm').joinpath('agents')
                if agents_path.exists():
                    return Path(str(agents_path))
            else:
                # For Python 3.7-3.8, use the backport approach
                from importlib import resources
                with resources.path('claude_mpm', 'agents') as agents_path:
                    if agents_path.exists():
                        return agents_path
        except (ImportError, ModuleNotFoundError, TypeError):
            # Fall back to manual detection if importlib.resources fails
            pass
        
        # Fallback to manual detection
        framework_root = cls.get_framework_root()
        
        # First check if we're in development structure (framework_root is project root)
        # This happens when framework_root has a src/ directory
        if (framework_root / 'src').exists():
            agents_dir = framework_root / 'src' / 'claude_mpm' / 'agents'
            if agents_dir.exists():
                return agents_dir
        
        # Otherwise we're in installed structure (framework_root is claude_mpm package)
        # In pip/pipx installs, framework_root already points to claude_mpm package
        agents_dir = framework_root / 'agents'
        if agents_dir.exists():
            return agents_dir
        
        # Last fallback for edge cases
        agents_dir = framework_root / 'claude_mpm' / 'agents'
        if agents_dir.exists():
            return agents_dir
        
        raise FileNotFoundError(
            f"Agents directory not found. Searched in:\n"
            f"  - importlib.resources lookup\n"
            f"  - {framework_root / 'src' / 'claude_mpm' / 'agents'} (development)\n"
            f"  - {framework_root / 'agents'} (installed)\n"
            f"  - {framework_root / 'claude_mpm' / 'agents'} (fallback)"
        )
    
    @classmethod
    @lru_cache(maxsize=1)
    def get_project_root(cls) -> Path:
        """Find the current project root.
        
        Searches for project markers like .git, pyproject.toml, package.json, etc.
        
        Returns:
            Path: The current project root directory
            
        Raises:
            FileNotFoundError: If no project root can be determined
        """
        # Project root markers in order of preference
        markers = ['.git', 'pyproject.toml', 'package.json', 'Cargo.toml', 
                   'go.mod', 'pom.xml', 'build.gradle', ConfigPaths.CONFIG_DIR]
        
        current = Path.cwd()
        while current != current.parent:
            for marker in markers:
                if (current / marker).exists():
                    logger.debug(f"Found project root at {current} via {marker}")
                    return current
            current = current.parent
        
        # If no markers found, use current directory
        logger.warning("No project markers found, using current directory as project root")
        return Path.cwd()
    
    @classmethod
    @lru_cache(maxsize=4)
    def get_config_dir(cls, scope: str = 'project') -> Path:
        """Get configuration directory for the specified scope.
        
        Args:
            scope: One of 'project', 'user', 'system', or 'framework'
            
        Returns:
            Path: The configuration directory
            
        Raises:
            ValueError: If scope is invalid
            FileNotFoundError: If directory cannot be determined
        """
        if scope == 'project':
            return cls.get_project_root() / ConfigPaths.CONFIG_DIR
        elif scope == 'user':
            # Support XDG_CONFIG_HOME if set
            xdg_config = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config:
                return Path(xdg_config) / 'claude-mpm'
            return Path.home() / '.config' / 'claude-mpm'
        elif scope == 'system':
            # System-wide configuration
            if os.name == 'posix':
                return Path('/etc/claude-mpm')
            else:
                # Windows: Use ProgramData
                return Path(os.environ.get('ProgramData', 'C:\\ProgramData')) / 'claude-mpm'
        elif scope == 'framework':
            return cls.get_framework_root() / ConfigPaths.CONFIG_DIR
        else:
            raise ValueError(f"Invalid scope: {scope}. Must be one of: project, user, system, framework")
    
    @classmethod
    def find_file_upwards(cls, filename: str, start_path: Optional[Path] = None) -> Optional[Path]:
        """Generic upward file search.
        
        Searches for a file by traversing up the directory tree.
        
        Args:
            filename: Name of the file to search for
            start_path: Starting directory (defaults to current directory)
            
        Returns:
            Path: Full path to the found file, or None if not found
        """
        current = Path(start_path) if start_path else Path.cwd()
        
        while current != current.parent:
            target = current / filename
            if target.exists():
                logger.debug(f"Found {filename} at {target}")
                return target
            current = current.parent
        
        logger.debug(f"Could not find {filename} in any parent directory")
        return None
    
    @classmethod
    @lru_cache(maxsize=8)
    def get_claude_pm_dir(cls, base_path: Optional[Path] = None) -> Optional[Path]:
        """Find .claude-mpm directory starting from base_path.
        
        Args:
            base_path: Starting directory (defaults to current directory)
            
        Returns:
            Path: The .claude-mpm directory, or None if not found
        """
        result = cls.find_file_upwards(ConfigPaths.CONFIG_DIR, base_path)
        return result if result and result.is_dir() else None
    
    @classmethod
    def ensure_directory(cls, path: Path) -> Path:
        """Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Directory path to ensure exists
            
        Returns:
            Path: The directory path
            
        Raises:
            OSError: If directory cannot be created
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError as e:
            logger.error(f"Failed to create directory {path}: {e}")
            raise
    
    @classmethod
    def get_relative_to_root(cls, path: Union[str, Path], root_type: str = 'project') -> Path:
        """Get a path relative to a specific root.
        
        Args:
            path: Relative path within the root
            root_type: Type of root ('project' or 'framework')
            
        Returns:
            Path: Full path relative to the specified root
            
        Raises:
            ValueError: If root_type is invalid
        """
        if root_type == 'project':
            root = cls.get_project_root()
        elif root_type == 'framework':
            root = cls.get_framework_root()
        else:
            raise ValueError(f"Invalid root_type: {root_type}. Must be 'project' or 'framework'")
        
        return root / path
    
    @classmethod
    def find_files_by_pattern(cls, pattern: str, root: Optional[Path] = None) -> List[Path]:
        """Find all files matching a pattern within a directory tree.
        
        Args:
            pattern: Glob pattern to match (e.g., '*.py', '**/*.md')
            root: Root directory to search (defaults to project root)
            
        Returns:
            List[Path]: List of matching file paths
        """
        if root is None:
            root = cls.get_project_root()
        
        matches = list(root.glob(pattern))
        logger.debug(f"Found {len(matches)} files matching '{pattern}' in {root}")
        return matches
    
    @classmethod
    def get_package_resource_path(cls, resource_path: str) -> Path:
        """Get the path to a resource within the claude_mpm package.
        
        This method handles both development and installed environments correctly.
        
        Args:
            resource_path: Relative path within the claude_mpm package (e.g., 'agents/templates')
            
        Returns:
            Path: Full path to the resource
            
        Raises:
            FileNotFoundError: If the resource doesn't exist
        """
        # Try using importlib.resources first (most reliable for installed packages)
        try:
            if sys.version_info >= (3, 9):
                from importlib.resources import files
                resource = files('claude_mpm').joinpath(resource_path)
                if resource.exists():
                    return Path(str(resource))
            else:
                # For Python 3.7-3.8
                from importlib import resources
                parts = resource_path.split('/')
                if len(parts) == 1:
                    with resources.path('claude_mpm', parts[0]) as p:
                        if p.exists():
                            return p
                else:
                    # For nested paths, navigate step by step
                    package = 'claude_mpm'
                    for part in parts[:-1]:
                        package = f"{package}.{part}"
                    with resources.path(package, parts[-1]) as p:
                        if p.exists():
                            return p
        except (ImportError, ModuleNotFoundError, TypeError, AttributeError):
            # Fall back to file system detection
            pass
        
        # Fallback: Use file system detection
        import claude_mpm
        module_path = Path(claude_mpm.__file__).parent
        resource = module_path / resource_path
        
        if resource.exists():
            return resource
        
        # Try with framework root
        framework_root = cls.get_framework_root()
        if (framework_root / 'src').exists():
            # Development environment
            resource = framework_root / 'src' / 'claude_mpm' / resource_path
        else:
            # Installed environment
            resource = framework_root / resource_path
        
        if resource.exists():
            return resource
        
        raise FileNotFoundError(f"Resource not found: {resource_path}")
    
    @classmethod
    def clear_cache(cls):
        """Clear all cached path lookups.
        
        Useful for testing or when the file system structure changes.
        """
        # Clear all lru_cache instances
        cls.get_framework_root.cache_clear()
        cls.get_agents_dir.cache_clear()
        cls.get_project_root.cache_clear()
        cls.get_config_dir.cache_clear()
        cls.get_claude_pm_dir.cache_clear()
        logger.debug("Cleared all PathResolver caches")


# Convenience functions for backward compatibility
def get_framework_root() -> Path:
    """Get the framework root directory."""
    return PathResolver.get_framework_root()


def get_project_root() -> Path:
    """Get the current project root directory."""
    return PathResolver.get_project_root()


def find_file_upwards(filename: str, start_path: Optional[Path] = None) -> Optional[Path]:
    """Search for a file by traversing up the directory tree."""
    return PathResolver.find_file_upwards(filename, start_path)


def get_package_resource_path(resource_path: str) -> Path:
    """Get the path to a resource within the claude_mpm package."""
    return PathResolver.get_package_resource_path(resource_path)