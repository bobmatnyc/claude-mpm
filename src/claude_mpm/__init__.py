"""Claude MPM - Multi-Agent Project Manager."""

from ._version import __version__
__author__ = "Claude MPM Team"

# Import main components
from .orchestration.orchestrator import MPMOrchestrator
from .core.framework_loader import FrameworkLoader
from .services.ticket_manager import TicketManager

__all__ = [
    "MPMOrchestrator",
    "FrameworkLoader", 
    "TicketManager",
]