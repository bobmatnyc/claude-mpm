"""Path resolution utilities for Claude MPM.

This module provides centralized path discovery and resolution logic
to avoid duplication across the codebase.
"""

import os
from pathlib import Path
from typing import Optional, Union, List
from functools import lru_cache
import logging

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
            # Go up to find the src directory, then one more for root
            if module_path.parent.name == 'src':
                return module_path.parent.parent
            # Otherwise, assume we're in site-packages
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
        framework_root = cls.get_framework_root()
        
        # Check for development structure
        agents_dir = framework_root / 'src' / 'claude_mpm' / 'agents'
        if agents_dir.exists():
            return agents_dir
        
        # Check for installed structure
        agents_dir = framework_root / 'claude_mpm' / 'agents'
        if agents_dir.exists():
            return agents_dir
        
        raise FileNotFoundError(
            f"Agents directory not found. Searched in:\n"
            f"  - {framework_root / 'src' / 'claude_mpm' / 'agents'}\n"
            f"  - {framework_root / 'claude_mpm' / 'agents'}"
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
                   'go.mod', 'pom.xml', 'build.gradle', '.claude-pm']
        
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
            return cls.get_project_root() / '.claude-pm'
        elif scope == 'user':
            # Support XDG_CONFIG_HOME if set
            xdg_config = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config:
                return Path(xdg_config) / 'claude-pm'
            return Path.home() / '.config' / 'claude-pm'
        elif scope == 'system':
            # System-wide configuration
            if os.name == 'posix':
                return Path('/etc/claude-pm')
            else:
                # Windows: Use ProgramData
                return Path(os.environ.get('ProgramData', 'C:\\ProgramData')) / 'claude-pm'
        elif scope == 'framework':
            return cls.get_framework_root() / '.claude-pm'
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
        """Find .claude-pm directory starting from base_path.
        
        Args:
            base_path: Starting directory (defaults to current directory)
            
        Returns:
            Path: The .claude-pm directory, or None if not found
        """
        result = cls.find_file_upwards('.claude-pm', base_path)
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