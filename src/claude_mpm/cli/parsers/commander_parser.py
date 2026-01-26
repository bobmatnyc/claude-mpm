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
        help="Launch Commander multi-project orchestration (ALPHA)",
        description="""
Commander Mode - Multi-Project Orchestration (ALPHA)

The commander subcommand auto-starts the Commander daemon (if not already running)
and launches an interactive REPL for managing multiple Claude Code instances.

Commander provides:
- Auto-starting daemon that manages project lifecycles
- Interactive REPL for controlling instances
- Tmux-based session management
- Real-time output monitoring
- REST API for external control (http://127.0.0.1:8765)

REPL Commands:
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
  # Start daemon and launch interactive chat
  claude-mpm commander

  # Start daemon only (no chat interface)
  claude-mpm commander --daemon-only

  # Use custom port
  claude-mpm commander --port 9000

  # In REPL:
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
        default=8766,  # NetworkPorts.COMMANDER_DEFAULT
        help="Port for internal services (default: 8766)",
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

    # Daemon auto-start options
    commander_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Daemon host (default: 127.0.0.1)",
    )

    commander_parser.add_argument(
        "--no-chat",
        action="store_true",
        help="Start daemon only without interactive chat",
    )

    commander_parser.add_argument(
        "--daemon-only",
        action="store_true",
        help="Alias for --no-chat (start daemon only)",
    )

    commander_parser.add_argument(
        "--force",
        action="store_true",
        help="Force kill any process using the port (use with caution)",
    )
