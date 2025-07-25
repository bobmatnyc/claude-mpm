"""Claude MPM - Multi-Agent Project Manager."""

from ._version import __version__
__author__ = "Claude MPM Team"

# Import main components
from .core.simple_runner import SimpleClaudeRunner
from .services.ticket_manager import TicketManager

# For backwards compatibility
MPMOrchestrator = SimpleClaudeRunner

__all__ = [
    "SimpleClaudeRunner",
    "MPMOrchestrator", 
    "TicketManager",
]