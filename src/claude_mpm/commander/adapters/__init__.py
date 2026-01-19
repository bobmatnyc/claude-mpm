"""Runtime adapters for MPM Commander.

This package provides adapters for different AI coding tools, allowing
the TmuxOrchestrator to interface with various runtimes in a uniform way.

Two types of adapters:
- RuntimeAdapter: Synchronous parsing and state detection
- CommunicationAdapter: Async I/O and state management

Available Runtime Adapters:
- ClaudeCodeAdapter: Vanilla Claude Code CLI
- AuggieAdapter: Auggie with MCP support
- CodexAdapter: Codex (limited features)
- MPMAdapter: Full MPM with agents, hooks, skills, monitoring

Registry:
- AdapterRegistry: Centralized adapter management with auto-detection
"""

from .auggie import AuggieAdapter
from .base import (
    Capability,
    ParsedResponse,
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeInfo,
)
from .claude_code import ClaudeCodeAdapter
from .codex import CodexAdapter
from .communication import (
    AdapterResponse,
    AdapterState,
    BaseCommunicationAdapter,
    ClaudeCodeCommunicationAdapter,
)
from .mpm import MPMAdapter
from .registry import AdapterRegistry

# Auto-register all adapters
AdapterRegistry.register("claude-code", ClaudeCodeAdapter)
AdapterRegistry.register("auggie", AuggieAdapter)
AdapterRegistry.register("codex", CodexAdapter)
AdapterRegistry.register("mpm", MPMAdapter)

__all__ = [
    "AdapterRegistry",
    "AdapterResponse",
    "AdapterState",
    "AuggieAdapter",
    "BaseCommunicationAdapter",
    "Capability",
    "ClaudeCodeAdapter",
    "ClaudeCodeCommunicationAdapter",
    "CodexAdapter",
    "MPMAdapter",
    "ParsedResponse",
    "RuntimeAdapter",
    "RuntimeCapability",
    "RuntimeInfo",
]
