"""Claude MPM - Multi-Agent Project Manager."""

from pathlib import Path

# Get version from VERSION file - single source of truth
version_file = Path(__file__).parent.parent.parent / "VERSION"
if version_file.exists():
    __version__ = version_file.read_text().strip()
else:
    # Default version if VERSION file is missing
    __version__ = "0.0.0"

__author__ = "Claude MPM Team"

# Import main components
from .core.claude_runner import ClaudeRunner
from .services.ticket_manager import TicketManager

# For backwards compatibility
MPMOrchestrator = ClaudeRunner

__all__ = [
    "ClaudeRunner",
    "MPMOrchestrator", 
    "TicketManager",
]