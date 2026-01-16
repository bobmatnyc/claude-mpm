"""Runtime adapters for MPM Commander.

This package provides adapters for different AI coding tools, allowing
the TmuxOrchestrator to interface with various runtimes in a uniform way.

Two types of adapters:
- RuntimeAdapter: Synchronous parsing and state detection
- CommunicationAdapter: Async I/O and state management
"""

from .base import Capability, ParsedResponse, RuntimeAdapter
from .claude_code import ClaudeCodeAdapter
from .communication import (
    AdapterResponse,
    AdapterState,
    BaseCommunicationAdapter,
    ClaudeCodeCommunicationAdapter,
)

__all__ = [
    # Communication adapters (async I/O)
    "AdapterResponse",
    "AdapterState",
    "BaseCommunicationAdapter",
    # Runtime adapters (parsing)
    "Capability",
    "ClaudeCodeAdapter",
    "ClaudeCodeCommunicationAdapter",
    "ParsedResponse",
    "RuntimeAdapter",
]
