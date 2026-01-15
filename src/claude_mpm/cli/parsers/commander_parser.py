"""
Commander parser module for claude-mpm CLI.

WHY: This module provides the commander subcommand for interactive instance management
and chat interface.

DESIGN DECISION: Uses subparser pattern consistent with other commands (run, agents, etc.)
to provide a clean interface for Commander mode.
"""

import argparse
from pathlib import Path


def add_commander_subparser(subparsers: argparse._SubParsersAction) -> None:
    """
    Add commander subcommand parser.

    WHY: Provides interactive mode for managing and chatting with multiple Claude instances.

    Args:
        subparsers: The subparsers object to add the commander parser to
    """
    commander_parser = subparsers.add_parser(
        "commander",
        help="Interactive Commander mode for managing multiple Claude instances",
        description="""
Commander Mode - Interactive Instance Management

Commander provides an interactive REPL interface for:
- Starting and stopping Claude Code/MPM instances in tmux
- Connecting to instances and sending natural language commands
- Managing multiple concurrent projects
- Viewing instance status and output

Commands:
  list, ls, instances   List active instances
  start <path>          Start new instance at path
    --framework <cc|mpm>  Specify framework (default: cc)
    --name <name>         Specify instance name (default: dir name)
  stop <name>           Stop an instance
  connect <name>        Connect to an instance
  disconnect            Disconnect from current instance
  status                Show current session status
  help                  Show help message
  exit, quit, q         Exit Commander

Natural Language:
  When connected to an instance, any input that is not a built-in
  command will be sent to the connected instance as a message.

Examples:
  claude-mpm commander
  > start ~/myproject --framework cc --name myapp
  > connect myapp
  > Fix the authentication bug in login.py
  > disconnect
  > exit
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Optional: Port for internal services
    commander_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for internal services (default: 8765)",
    )

    # Optional: State directory
    commander_parser.add_argument(
        "--state-dir",
        type=Path,
        help="Directory for state persistence (optional)",
    )

    # Debug mode
    commander_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
