"""Claude MPM - Multi-Agent Project Manager."""

from pathlib import Path

# Get version from VERSION file - single source of truth
# Try package VERSION file first (for installed packages)
package_version_file = Path(__file__).parent / "VERSION"
if package_version_file.exists():
    __version__ = package_version_file.read_text().strip()
else:
    # Fall back to project root VERSION file (for development)
    root_version_file = Path(__file__).parent.parent.parent / "VERSION"
    if root_version_file.exists():
        __version__ = root_version_file.read_text().strip()
    else:
        # Default version if VERSION file is missing
        __version__ = "0.0.0"

# For development builds, append build number if available (PEP 440 format)
# This creates versions like "3.9.5+build.275" for local development
try:
    build_file = Path(__file__).parent.parent.parent / "BUILD_NUMBER"
    if build_file.exists():
        build_number = build_file.read_text().strip()
        if build_number.isdigit():
            # Use PEP 440 local version identifier format for development
            __version__ = f"{__version__}+build.{build_number}"
except Exception:
    # Ignore any errors reading build number
    pass

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
