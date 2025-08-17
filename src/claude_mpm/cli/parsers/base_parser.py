from pathlib import Path

"""
Base parser module for claude-mpm CLI.

WHY: This module contains the main parser factory and common argument definitions
that are shared across all commands. Extracted from the monolithic parser.py.

DESIGN DECISION: Common arguments are defined once and reused to ensure consistency
and reduce duplication across command parsers.
"""

import argparse
from typing import List, Optional

from ...constants import CLICommands, CLIPrefix, LogLevel


def add_common_arguments(parser: argparse.ArgumentParser, version: str = None) -> None:
    """
    Add common arguments that apply to all commands.

    WHY: These arguments are needed across multiple commands, so we centralize them
    to ensure consistency and avoid duplication.

    Args:
        parser: The argument parser to add arguments to
        version: Version string to display (only needed for main parser)
    """
    # Version - only add to main parser, not subparsers
    if version is not None:
        parser.add_argument("--version", action="version", version=f"%(prog)s {version}")

    # Logging arguments
    logging_group = parser.add_argument_group("logging options")
    logging_group.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logging (deprecated, use --logging DEBUG)",
    )
    logging_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (deprecated, use --logging INFO)",
    )
    logging_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output except errors (deprecated, use --logging ERROR)",
    )
    logging_group.add_argument(
        "--logging",
        choices=[level.value for level in LogLevel],
        help="Set logging level (overrides -d, -v, -q flags)",
    )

    # Configuration arguments
    config_group = parser.add_argument_group("configuration options")
    config_group.add_argument("--config", type=Path, help="Path to configuration file")
    config_group.add_argument(
        "--project-dir", type=Path, help="Project directory (overrides auto-detection)"
    )


def create_main_parser(
    prog_name: str = "claude-mpm", version: str = "0.0.0"
) -> argparse.ArgumentParser:
    """
    Create the main argument parser with basic setup.

    WHY: This creates the foundation parser that other modules will extend
    with their specific subcommands and arguments.

    Args:
        prog_name: The program name to use
        version: The version string to display

    Returns:
        Configured ArgumentParser instance ready for subparser addition
    """
    # Main parser
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description=f"Claude Multi-Agent Project Manager v{version} - Orchestrate Claude with agent delegation and ticket tracking",
        epilog="By default, runs an orchestrated Claude session. Use 'claude-mpm' for interactive mode or 'claude-mpm -i \"prompt\"' for non-interactive mode.\n\nTo pass arguments to Claude CLI, use -- separator: claude-mpm run -- --model sonnet --temperature 0.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Add common arguments to main parser with version
    add_common_arguments(parser, version=version)

    return parser


def add_top_level_run_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add run-specific arguments at top level for backward compatibility.

    WHY: This maintains backward compatibility - users can run `claude-mpm -i "prompt"`
    without specifying the 'run' command.

    Args:
        parser: The argument parser to add arguments to
    """
    # Add run-specific arguments at top level for default behavior
    # NOTE: We don't add claude_args here because REMAINDER interferes with subcommands
    run_group = parser.add_argument_group("run options (when no command specified)")

    run_group.add_argument(
        "--no-hooks", action="store_true", help="Disable hook service (runs without hooks)"
    )
    run_group.add_argument(
        "--no-tickets", action="store_true", help="Disable automatic ticket creation"
    )
    run_group.add_argument(
        "--intercept-commands",
        action="store_true",
        help="Enable command interception in interactive mode (intercepts /mpm: commands)",
    )
    run_group.add_argument(
        "--no-native-agents",
        action="store_true",
        help="Disable deployment of Claude Code native agents",
    )
    run_group.add_argument(
        "--launch-method",
        choices=["exec", "subprocess"],
        default="exec",
        help="Method to launch Claude: exec (replace process) or subprocess (child process)",
    )
    # Monitor options - consolidated monitoring and management interface
    run_group.add_argument(
        "--monitor",
        action="store_true",
        help="Enable monitoring and management interface with WebSocket server and dashboard (default port: 8765)",
    )
    run_group.add_argument(
        "--websocket-port", type=int, default=8765, help="WebSocket server port (default: 8765)"
    )
    run_group.add_argument(
        "--resume",
        type=str,
        nargs="?",
        const="last",
        help="Resume a session (last session if no ID specified, or specific session ID)",
    )
    run_group.add_argument(
        "--force",
        action="store_true",
        help="Force operations even with warnings (e.g., large .claude.json file)",
    )

    # Dependency checking options (for backward compatibility at top level)
    dep_group_top = parser.add_argument_group("dependency options (when no command specified)")
    dep_group_top.add_argument(
        "--no-check-dependencies",
        action="store_false",
        dest="check_dependencies",
        help="Skip agent dependency checking at startup",
    )
    dep_group_top.add_argument(
        "--force-check-dependencies",
        action="store_true",
        help="Force dependency checking even if cached results exist",
    )
    dep_group_top.add_argument(
        "--no-prompt",
        action="store_true",
        help="Never prompt for dependency installation (non-interactive mode)",
    )
    dep_group_top.add_argument(
        "--force-prompt",
        action="store_true",
        help="Force interactive prompting even in non-TTY environments (use with caution)",
    )

    # Input/output options
    io_group = parser.add_argument_group("input/output options (when no command specified)")
    io_group.add_argument(
        "-i", "--input", type=str, help="Input text or file path (for non-interactive mode)"
    )
    io_group.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (read from stdin or --input)",
    )


def create_parser(prog_name: str = "claude-mpm", version: str = "0.0.0") -> argparse.ArgumentParser:
    """
    Create the main argument parser with all subcommands.

    WHY: This factory function creates a complete parser with all commands and their
    arguments. It's the single entry point for creating the CLI parser, ensuring
    consistency across the application.

    DESIGN DECISION: We use subparsers for commands to provide a clean, git-like
    interface while maintaining backward compatibility with the original CLI.

    Args:
        prog_name: The program name to use
        version: The version string to display

    Returns:
        Configured ArgumentParser instance
    """
    # Create main parser
    parser = create_main_parser(prog_name, version)

    # Add top-level run arguments for backward compatibility
    add_top_level_run_arguments(parser)

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands", metavar="COMMAND")

    # Import and add core subparsers one by one to avoid issues
    try:
        from .run_parser import add_run_subparser

        add_run_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .tickets_parser import add_tickets_subparser

        add_tickets_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .agents_parser import add_agents_subparser

        add_agents_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .memory_parser import add_memory_subparser

        add_memory_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .config_parser import add_config_subparser

        add_config_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .monitor_parser import add_monitor_subparser

        add_monitor_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .mcp_parser import add_mcp_subparser

        add_mcp_subparser(subparsers)
    except ImportError:
        pass

    # Import and add additional command parsers from commands module
    try:
        from ..commands.aggregate import add_aggregate_parser

        add_aggregate_parser(subparsers)

        from ..commands.cleanup import add_cleanup_parser

        add_cleanup_parser(subparsers)

        from ..commands.run_guarded import add_run_guarded_parser

        add_run_guarded_parser(subparsers)
    except ImportError:
        # Commands module may not be available during testing or refactoring
        pass

    return parser


def preprocess_args(argv: Optional[List[str]] = None) -> List[str]:
    """
    Preprocess arguments to handle --mpm: prefix commands.

    WHY: We support both --mpm:command and regular command syntax for flexibility
    and backward compatibility. This function normalizes the input.

    Args:
        argv: List of command line arguments, or None to use sys.argv[1:]

    Returns:
        Processed list of arguments with prefixes removed
    """
    import sys

    if argv is None:
        argv = sys.argv[1:]

    # Convert --mpm:command to command for argparse compatibility
    processed_args = []
    for arg in argv:
        if arg.startswith(CLIPrefix.MPM.value):
            # Extract command after prefix
            command = arg[len(CLIPrefix.MPM.value) :]
            processed_args.append(command)
        else:
            processed_args.append(arg)

    return processed_args
