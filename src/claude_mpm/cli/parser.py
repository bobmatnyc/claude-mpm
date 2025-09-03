"""
Argument parser for claude-mpm CLI.

WHY: This module provides backward compatibility and delegates to the new modular
parser structure. The massive create_parser function has been split into focused
modules in the parsers/ package.

DESIGN DECISION: We maintain this file for backward compatibility while the actual
parser logic has been moved to parsers/ modules for better maintainability.

REFACTORING NOTE: The original 961-line create_parser function has been split into:
- parsers/base_parser.py: Common arguments and main parser setup
- parsers/run_parser.py: Run command arguments
- parsers/agents_parser.py: Agent management commands
- parsers/memory_parser.py: Memory management commands
- parsers/tickets_parser.py: Ticket management commands
- parsers/config_parser.py: Configuration commands
- parsers/monitor_parser.py: Monitoring commands
- parsers/mcp_parser.py: MCP Gateway commands
"""

import argparse
import sys
from typing import List, Optional

# Try to import from the new modular structure with helpful error handling
try:
    from .parsers import add_common_arguments, create_parser, preprocess_args
except ImportError as e:
    # Provide a helpful error message for users with outdated installations
    error_msg = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    Claude MPM Import Error                       ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  Unable to import required modules: {e!s}                     ║
║                                                                   ║
║  This typically happens when:                                    ║
║  • The installation is outdated or incomplete                    ║
║  • Files are missing from your installation                      ║
║  • You're using an old cached version from pipx                  ║
║                                                                   ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │ To fix this issue, please try one of these solutions:   │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                   ║
║  1. If installed with pipx (recommended):                        ║
║     ➜ pipx reinstall claude-mpm                                  ║
║                                                                   ║
║  2. If installed with pip:                                       ║
║     ➜ pip install --upgrade --force-reinstall claude-mpm        ║
║                                                                   ║
║  3. For development installations:                               ║
║     ➜ pip install -e . --force-reinstall                        ║
║                                                                   ║
║  4. Clear pipx cache and reinstall (if pipx issues persist):    ║
║     ➜ pipx uninstall claude-mpm                                  ║
║     ➜ pipx install claude-mpm                                    ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(error_msg, file=sys.stderr)

    # Provide minimal fallback functionality to at least show help
    def create_parser(version: str = "Unknown") -> argparse.ArgumentParser:
        """Emergency fallback parser that shows reinstallation instructions."""
        parser = argparse.ArgumentParser(
            prog="claude-mpm",
            description="Claude Multi-Agent Project Manager (Installation Error - Please Reinstall)",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
This installation appears to be incomplete or outdated.
Please reinstall using one of the methods shown above.
            """,
        )
        parser.add_argument(
            "--version",
            action="version",
            version=f"{version} (installation error - please reinstall)",
        )
        return parser

    def add_common_arguments(parser: argparse.ArgumentParser) -> None:
        """Emergency fallback - no common arguments available."""

    def preprocess_args(args: Optional[List[str]] = None) -> List[str]:
        """Emergency fallback - return args unchanged."""
        return args if args is not None else sys.argv[1:]

    # Exit with error code to indicate the problem
    # Don't exit immediately - let the user see --help if requested
    import atexit

    atexit.register(
        lambda: (
            sys.exit(1)
            if "--help" not in sys.argv and "--version" not in sys.argv
            else None
        )
    )

# Re-export for backward compatibility
__all__ = ["add_common_arguments", "create_parser", "preprocess_args"]

# Legacy functions removed - all functionality moved to parsers/ modules
# The original parser.py file contained a massive 961-line create_parser function
# that has been split into focused modules for better maintainability.
