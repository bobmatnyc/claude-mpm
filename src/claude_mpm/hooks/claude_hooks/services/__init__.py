"""Hook handler services for modular functionality."""

# Use HTTP-based connection manager for stable dashboard communication
# from .connection_manager import ConnectionManagerService  # Old SocketIO-based
from .connection_manager_http import ConnectionManagerService  # New HTTP-based
from .container import HookServiceContainer, get_container
from .duplicate_detector import DuplicateEventDetector
from .protocols import (
    IAutoPauseHandler,
    IConnectionManager,
    IDuplicateDetector,
    IEventHandlers,
    IMemoryHookManager,
    IResponseTrackingManager,
    IStateManager,
    ISubagentProcessor,
)
from .state_manager import StateManagerService
from .subagent_processor import SubagentResponseProcessor

__all__ = [
    "ConnectionManagerService",
    "DuplicateEventDetector",
    "HookServiceContainer",
    "IAutoPauseHandler",
    "IConnectionManager",
    "IDuplicateDetector",
    "IEventHandlers",
    "IMemoryHookManager",
    "IResponseTrackingManager",
    "IStateManager",
    "ISubagentProcessor",
    "StateManagerService",
    "SubagentResponseProcessor",
    "get_container",
]
