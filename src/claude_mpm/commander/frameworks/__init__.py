"""Framework abstractions for AI coding assistants."""

from .base import BaseFramework, InstanceInfo
from .claude_code import ClaudeCodeFramework
from .mpm import MPMFramework

__all__ = [
    "BaseFramework",
    "ClaudeCodeFramework",
    "InstanceInfo",
    "MPMFramework",
]
