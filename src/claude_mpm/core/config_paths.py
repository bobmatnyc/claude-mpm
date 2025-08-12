"""
Centralized configuration paths for claude-mpm.

This module provides a single source of truth for all configuration-related paths
throughout the codebase. All modules should import and use these constants
instead of hardcoding directory names.
"""

from enum import Enum
from pathlib import Path
from typing import Optional


class ConfigDirName(Enum):
    """Enum for configuration directory names to ensure type safety."""
    CLAUDE_MPM = ".claude-mpm"


# Core configuration directory name - MUST be consistent everywhere
CONFIG_DIR_NAME = ConfigDirName.CLAUDE_MPM.value

# Legacy name that should NOT be used (kept for reference during migration)
_LEGACY_CONFIG_DIR_NAME = ".claude-pm"  # DO NOT USE THIS


class ConfigPaths:
    """Centralized configuration path constants."""
    
    # Base directory names
    CONFIG_DIR = ConfigDirName.CLAUDE_MPM.value
    AGENTS_DIR = "agents"
    BACKUPS_DIR = "backups"
    TRACKING_DIR = "agent_tracking"
    MEMORIES_DIR = "memories"
    RESPONSES_DIR = "responses"
    
    # Agent subdirectories
    AGENT_USER_AGENTS = "user-agents"
    AGENT_USER_DEFINED = "user-defined"
    AGENT_SYSTEM = "templates"
    
    # Configuration files
    CONFIG_FILE = "config.json"
    CONFIGURATION_YAML = "configuration.yaml"
    LIFECYCLE_RECORDS = "lifecycle_records.json"
    VERSION_FILE = "VERSION"
    INSTRUCTIONS_FILE = "INSTRUCTIONS.md"
    
    @classmethod
    def get_user_config_dir(cls) -> Path:
        """Get the user-level configuration directory."""
        return Path.home() / cls.CONFIG_DIR
    
    @classmethod
    def get_project_config_dir(cls, project_root: Optional[Path] = None) -> Path:
        """Get the project-level configuration directory."""
        root = project_root or Path.cwd()
        return root / cls.CONFIG_DIR
    
    @classmethod
    def get_framework_config_dir(cls, framework_root: Path) -> Path:
        """Get the framework-level configuration directory."""
        return framework_root / cls.CONFIG_DIR
    
    @classmethod
    def get_user_agents_dir(cls) -> Path:
        """Get the user-level agents directory."""
        return cls.get_user_config_dir() / cls.AGENTS_DIR
    
    @classmethod
    def get_project_agents_dir(cls, project_root: Optional[Path] = None) -> Path:
        """Get the project-level agents directory."""
        return cls.get_project_config_dir(project_root) / cls.AGENTS_DIR
    
    @classmethod
    def get_tracking_dir(cls) -> Path:
        """Get the agent tracking directory."""
        return cls.get_user_config_dir() / cls.TRACKING_DIR
    
    @classmethod
    def get_backups_dir(cls, base_dir: Optional[Path] = None) -> Path:
        """Get the backups directory."""
        if base_dir:
            return base_dir / cls.CONFIG_DIR / cls.BACKUPS_DIR
        return cls.get_user_config_dir() / cls.BACKUPS_DIR
    
    @classmethod
    def get_memories_dir(cls, base_dir: Optional[Path] = None) -> Path:
        """Get the memories directory."""
        if base_dir:
            return base_dir / cls.CONFIG_DIR / cls.MEMORIES_DIR
        return cls.get_project_config_dir() / cls.MEMORIES_DIR
    
    @classmethod
    def get_responses_dir(cls, base_dir: Optional[Path] = None) -> Path:
        """Get the responses directory."""
        if base_dir:
            return base_dir / cls.CONFIG_DIR / cls.RESPONSES_DIR
        return cls.get_project_config_dir() / cls.RESPONSES_DIR
    
    @classmethod
    def find_config_dir(cls, start_path: Optional[Path] = None) -> Optional[Path]:
        """
        Find the nearest configuration directory by walking up the directory tree.
        
        Args:
            start_path: Starting directory (defaults to current working directory)
            
        Returns:
            Path to the configuration directory if found, None otherwise
        """
        current = start_path or Path.cwd()
        
        # Check current directory and parents
        for path in [current] + list(current.parents):
            config_dir = path / cls.CONFIG_DIR
            if config_dir.exists():
                return config_dir
        
        return None
    
    @classmethod
    def validate_not_legacy(cls, path: Path) -> bool:
        """
        Check if a path contains the legacy configuration directory name.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is valid (not legacy), False if it contains legacy name
        """
        path_str = str(path)
        return _LEGACY_CONFIG_DIR_NAME not in path_str


# Export commonly used paths as module-level constants for convenience
USER_CONFIG_DIR = ConfigPaths.get_user_config_dir()
USER_AGENTS_DIR = ConfigPaths.get_user_agents_dir()
USER_TRACKING_DIR = ConfigPaths.get_tracking_dir()

# Export all public symbols
__all__ = [
    "ConfigDirName",
    "ConfigPaths",
    "CONFIG_DIR_NAME",
    "USER_CONFIG_DIR",
    "USER_AGENTS_DIR",
    "USER_TRACKING_DIR",
]