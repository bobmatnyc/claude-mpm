"""Core components for Claude MPM."""

from .agent_registry import AgentRegistryAdapter
from .framework_loader import FrameworkLoader
from .claude_launcher import ClaudeLauncher, LaunchMode
from .mixins import LoggerMixin

# Import config components if needed
try:
    from .config import Config
    from .config_aliases import ConfigAliases
except ImportError:
    pass

__all__ = [
    "AgentRegistryAdapter",
    "FrameworkLoader",
    "ClaudeLauncher",
    "LaunchMode",
    "LoggerMixin",
]