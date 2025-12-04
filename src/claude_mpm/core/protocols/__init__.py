"""Protocol interfaces for dependency injection.

This module defines Protocol interfaces to break circular dependencies
using Python's typing.Protocol feature for structural subtyping.
"""

from claude_mpm.core.protocols.runner_protocol import (
    ClaudeRunnerProtocol,
    SystemPromptProvider,
)
from claude_mpm.core.protocols.session_protocol import (
    InteractiveSessionProtocol,
    OneshotSessionProtocol,
    SessionManagementProtocol,
)

__all__ = [
    "ClaudeRunnerProtocol",
    "InteractiveSessionProtocol",
    "OneshotSessionProtocol",
    "SessionManagementProtocol",
    "SystemPromptProvider",
]
