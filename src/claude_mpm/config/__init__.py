"""Configuration module for claude-mpm."""

# Import only modules that exist
__all__ = []

# Try to import HookConfig if it exists
try:
    from .hook_config import HookConfig
    __all__.append('HookConfig')
except ImportError:
    pass

# Import AgentConfig
try:
    from .agent_config import AgentConfig, get_agent_config, set_agent_config, reset_agent_config
    __all__.extend(['AgentConfig', 'get_agent_config', 'set_agent_config', 'reset_agent_config'])
except ImportError:
    pass