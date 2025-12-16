# Copyright (c) 2024-2025 Bob Matsuoka
# Licensed under the Elastic License 2.0
# See LICENSE file in the project root for full license information.

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


# Lazy imports for main components to avoid loading heavy dependencies
# when only importing from submodules (e.g., core.logging_utils)
# This significantly improves hook handler performance
def __getattr__(name):
    """Lazy load main components only when accessed."""
    if name == "ClaudeRunner":
        from .core.claude_runner import ClaudeRunner

        return ClaudeRunner
    if name == "MPMOrchestrator":
        # For backwards compatibility
        from .core.claude_runner import ClaudeRunner

        return ClaudeRunner
    if name == "TicketManager":
        from .services.ticket_manager import TicketManager

        return TicketManager
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "ClaudeRunner",
    "MPMOrchestrator",
    "TicketManager",
]
