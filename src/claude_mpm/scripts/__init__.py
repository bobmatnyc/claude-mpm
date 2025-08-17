"""
Production scripts for claude-mpm.

WHY: This module contains production-ready scripts that can be run independently
for various claude-mpm operations like activity logging, monitoring, etc.

DESIGN DECISION: These scripts are kept as part of the main package rather than
in the top-level scripts/ directory to ensure they have proper access to the
claude_mpm module and can be distributed with the package.
"""

# Export commonly used scripts for programmatic access
from .start_activity_logging import signal_handler

__all__ = ["signal_handler"]
