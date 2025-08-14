"""Configuration module for claude-mpm."""

# Import only modules that exist
__all__ = []

# Import centralized path management
from .paths import (
    paths, 
    ClaudeMPMPaths,
    get_project_root,
    get_src_dir,
    get_claude_mpm_dir,
    get_agents_dir,
    get_services_dir,
    get_config_dir,
    get_version,
    ensure_src_in_path
)

# Import configuration classes - only those that exist
from .agent_config import AgentConfig, get_agent_config, set_agent_config, reset_agent_config

__all__.extend([
    'paths',
    'ClaudeMPMPaths', 
    'get_project_root',
    'get_src_dir',
    'get_claude_mpm_dir',
    'get_agents_dir',
    'get_services_dir',
    'get_config_dir',
    'get_version',
    'ensure_src_in_path',
    'AgentConfig',
    'get_agent_config',
    'set_agent_config',
    'reset_agent_config'
])