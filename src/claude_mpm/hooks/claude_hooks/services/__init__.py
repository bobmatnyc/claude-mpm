"""Hook handler services for modular functionality."""

# Use HTTP-based connection manager for stable dashboard communication
# from .connection_manager import ConnectionManagerService  # Old SocketIO-based
from .connection_manager_http import ConnectionManagerService  # New HTTP-based
from .duplicate_detector import DuplicateEventDetector
from .state_manager import StateManagerService
from .subagent_processor import SubagentResponseProcessor

__all__ = [
    "ConnectionManagerService",
    "DuplicateEventDetector",
    "StateManagerService",
    "SubagentResponseProcessor",
]
