"""
Argument parser for claude-mpm CLI.

WHY: This module centralizes all argument parsing logic to avoid duplication and provide
a single source of truth for CLI arguments. It uses inheritance to share common arguments
across commands while keeping command-specific args organized.

DESIGN DECISION: We use a base parser factory pattern to create parsers with common
arguments, then extend them for specific commands. This reduces duplication while
maintaining flexibility.
"""

import argparse
from pathlib import Path
from typing import Optional, List

from ..constants import CLICommands, CLIPrefix, AgentCommands, MemoryCommands, LogLevel


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
        parser.add_argument(
            "--version",
            action="version",
            version=f"%(prog)s {version}"
        )
    
    # Logging arguments
    logging_group = parser.add_argument_group('logging options')
    logging_group.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging (deprecated, use --logging DEBUG)"
    )
    logging_group.add_argument(
        "--logging",
        choices=[level.value for level in LogLevel],
        default=LogLevel.INFO.value,
        help="Logging level (default: INFO)"
    )
    logging_group.add_argument(
        "--log-dir",
        type=Path,
        help="Custom log directory (default: ~/.claude-mpm/logs)"
    )
    
    # Framework configuration
    framework_group = parser.add_argument_group('framework options')
    framework_group.add_argument(
        "--framework-path",
        type=Path,
        help="Path to claude-mpm framework"
    )
    framework_group.add_argument(
        "--agents-dir",
        type=Path,
        help="Custom agents directory to use"
    )


def add_run_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add arguments specific to the run command.
    
    WHY: The run command has specific arguments for controlling how Claude sessions
    are executed, including hook management, ticket creation, and interaction modes.
    
    Args:
        parser: The argument parser to add arguments to
    """
    run_group = parser.add_argument_group('run options')
    
    run_group.add_argument(
        "--no-hooks",
        action="store_true",
        help="Disable hook service (runs without hooks)"
    )
    run_group.add_argument(
        "--no-tickets",
        action="store_true",
        help="Disable automatic ticket creation"
    )
    run_group.add_argument(
        "--intercept-commands",
        action="store_true",
        help="Enable command interception in interactive mode (intercepts /mpm: commands)"
    )
    run_group.add_argument(
        "--no-native-agents",
        action="store_true",
        help="Disable deployment of Claude Code native agents"
    )
    run_group.add_argument(
        "--launch-method",
        choices=["exec", "subprocess"],
        default="exec",
        help="Method to launch Claude: exec (replace process) or subprocess (child process)"
    )
    # WebSocket options - make websocket and manager mutually exclusive
    websocket_group = run_group.add_mutually_exclusive_group()
    websocket_group.add_argument(
        "--websocket",
        action="store_true",
        help="Enable WebSocket server for real-time monitoring (default port: 8765)"
    )
    websocket_group.add_argument(
        "--manager",
        action="store_true",
        help="Start management interface with WebSocket server and dashboard"
    )
    run_group.add_argument(
        "--websocket-port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    
    # Input/output options
    io_group = parser.add_argument_group('input/output options')
    io_group.add_argument(
        "-i", "--input",
        type=str,
        help="Input text or file path (for non-interactive mode)"
    )
    io_group.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (read from stdin or --input)"
    )
    
    # Claude CLI arguments
    parser.add_argument(
        "claude_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to Claude CLI (use -- before Claude args)"
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
    # Main parser
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description=f"Claude Multi-Agent Project Manager v{version} - Orchestrate Claude with agent delegation and ticket tracking",
        epilog="By default, runs an orchestrated Claude session. Use 'claude-mpm' for interactive mode or 'claude-mpm -i \"prompt\"' for non-interactive mode.\n\nTo pass arguments to Claude CLI, use -- separator: claude-mpm run -- --model sonnet --temperature 0.1",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add common arguments to main parser with version
    add_common_arguments(parser, version=version)
    
    # Add run-specific arguments at top level for default behavior
    # WHY: This maintains backward compatibility - users can run `claude-mpm -i "prompt"`
    # without specifying the 'run' command
    # NOTE: We don't add claude_args here because REMAINDER interferes with subcommands
    run_group = parser.add_argument_group('run options (when no command specified)')
    
    run_group.add_argument(
        "--no-hooks",
        action="store_true",
        help="Disable hook service (runs without hooks)"
    )
    run_group.add_argument(
        "--no-tickets",
        action="store_true",
        help="Disable automatic ticket creation"
    )
    run_group.add_argument(
        "--intercept-commands",
        action="store_true",
        help="Enable command interception in interactive mode (intercepts /mpm: commands)"
    )
    run_group.add_argument(
        "--no-native-agents",
        action="store_true",
        help="Disable deployment of Claude Code native agents"
    )
    run_group.add_argument(
        "--launch-method",
        choices=["exec", "subprocess"],
        default="exec",
        help="Method to launch Claude: exec (replace process) or subprocess (child process)"
    )
    # WebSocket options - make websocket and manager mutually exclusive
    websocket_group = run_group.add_mutually_exclusive_group()
    websocket_group.add_argument(
        "--websocket",
        action="store_true",
        help="Enable WebSocket server for real-time monitoring (default port: 8765)"
    )
    websocket_group.add_argument(
        "--manager",
        action="store_true",
        help="Start management interface with WebSocket server and dashboard"
    )
    run_group.add_argument(
        "--websocket-port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    
    # Input/output options
    io_group = parser.add_argument_group('input/output options (when no command specified)')
    io_group.add_argument(
        "-i", "--input",
        type=str,
        help="Input text or file path (for non-interactive mode)"
    )
    io_group.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (read from stdin or --input)"
    )
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        metavar="COMMAND"
    )
    
    # Run command (explicit)
    run_parser = subparsers.add_parser(
        CLICommands.RUN.value,
        help="Run orchestrated Claude session (default)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_common_arguments(run_parser)
    add_run_arguments(run_parser)
    
    # Tickets command
    tickets_parser = subparsers.add_parser(
        CLICommands.TICKETS.value,
        help="List recent tickets"
    )
    add_common_arguments(tickets_parser)
    tickets_parser.add_argument(
        "-n", "--limit",
        type=int,
        default=10,
        help="Number of tickets to show"
    )
    
    # Info command
    info_parser = subparsers.add_parser(
        CLICommands.INFO.value,
        help="Show framework and configuration info"
    )
    add_common_arguments(info_parser)
    
    # UI command
    ui_parser = subparsers.add_parser(
        CLICommands.UI.value,
        help="Launch terminal UI with multiple panes"
    )
    add_common_arguments(ui_parser)
    ui_parser.add_argument(
        "--mode",
        choices=["terminal", "curses"],
        default="terminal",
        help="UI mode to launch (default: terminal)"
    )
    
    # Agents command with subcommands
    agents_parser = subparsers.add_parser(
        CLICommands.AGENTS.value,
        help="Manage Claude Code native agents"
    )
    add_common_arguments(agents_parser)
    
    agents_subparsers = agents_parser.add_subparsers(
        dest="agents_command",
        help="Agent commands",
        metavar="SUBCOMMAND"
    )
    
    # List agents
    list_agents_parser = agents_subparsers.add_parser(
        AgentCommands.LIST.value,
        help="List available agents"
    )
    list_agents_parser.add_argument(
        "--system",
        action="store_true",
        help="List system agents"
    )
    list_agents_parser.add_argument(
        "--deployed",
        action="store_true", 
        help="List deployed agents"
    )
    
    # Deploy agents
    deploy_agents_parser = agents_subparsers.add_parser(
        AgentCommands.DEPLOY.value,
        help="Deploy system agents"
    )
    deploy_agents_parser.add_argument(
        "--target",
        type=Path,
        help="Target directory (default: .claude/agents/)"
    )
    
    # Force deploy agents
    force_deploy_parser = agents_subparsers.add_parser(
        AgentCommands.FORCE_DEPLOY.value,
        help="Force deploy all system agents"
    )
    force_deploy_parser.add_argument(
        "--target",
        type=Path,
        help="Target directory (default: .claude/agents/)"
    )
    
    # Clean agents
    clean_agents_parser = agents_subparsers.add_parser(
        AgentCommands.CLEAN.value,
        help="Remove deployed system agents"
    )
    clean_agents_parser.add_argument(
        "--target",
        type=Path,
        help="Target directory (default: .claude/)"
    )
    
    # Memory command with subcommands
    memory_parser = subparsers.add_parser(
        CLICommands.MEMORY.value,
        help="Manage agent memory files"
    )
    add_common_arguments(memory_parser)
    
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command",
        help="Memory commands",
        metavar="SUBCOMMAND"
    )
    
    # Status command
    status_parser = memory_subparsers.add_parser(
        MemoryCommands.STATUS.value,
        help="Show memory file status"
    )
    
    # View command
    view_parser = memory_subparsers.add_parser(
        MemoryCommands.VIEW.value,
        help="View agent memory file"
    )
    view_parser.add_argument(
        "agent_id",
        help="Agent ID to view memory for"
    )
    
    # Add command
    add_parser = memory_subparsers.add_parser(
        MemoryCommands.ADD.value,
        help="Manually add learning to agent memory"
    )
    add_parser.add_argument(
        "agent_id",
        help="Agent ID to add learning to"
    )
    add_parser.add_argument(
        "learning_type",
        choices=["pattern", "error", "optimization", "preference", "context"],
        help="Type of learning to add"
    )
    add_parser.add_argument(
        "content",
        help="Learning content to add"
    )
    
    # Clean command
    clean_memory_parser = memory_subparsers.add_parser(
        MemoryCommands.CLEAN.value,
        help="Clean up old/unused memory files"
    )
    
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
            command = arg[len(CLIPrefix.MPM.value):]
            processed_args.append(command)
        else:
            processed_args.append(arg)
    
    return processed_args