"""Configuration module for claude-mpm."""

# Import only modules that exist
__all__ = []

# Import configuration classes - only those that exist
from .agent_config import (
    AgentConfig,
    get_agent_config,
    reset_agent_config,
    set_agent_config,
)

# Import centralized path management
from .paths import (
    ClaudeMPMPaths,
    ensure_src_in_path,
    get_agents_dir,
    get_claude_mpm_dir,
    get_config_dir,
    get_project_root,
    get_services_dir,
    get_src_dir,
    get_version,
    paths,
)

__all__.extend(
    [
        "AgentConfig",
        "ClaudeMPMPaths",
        "ensure_src_in_path",
        "get_agent_config",
        "get_agents_dir",
        "get_claude_mpm_dir",
        "get_config_dir",
        "get_project_root",
        "get_services_dir",
        "get_src_dir",
        "get_version",
        "paths",
        "reset_agent_config",
        "set_agent_config",
    ]
)
