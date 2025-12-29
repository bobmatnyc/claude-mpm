from pathlib import Path

"""
Base parser module for claude-mpm CLI.

WHY: This module contains the main parser factory and common argument definitions
that are shared across all commands. Extracted from the monolithic parser.py.

DESIGN DECISION: Common arguments are defined once and reused to ensure consistency
and reduce duplication across command parsers.
"""

import argparse
import sys
from typing import List, Optional

from ...constants import CLICommands, CLIPrefix, LogLevel


class SuggestingArgumentParser(argparse.ArgumentParser):
    """
    Custom ArgumentParser that suggests similar commands on error.

    WHY: Provides better user experience by suggesting corrections for typos
    and invalid commands instead of just showing an error message.

    DESIGN DECISION: Extends ArgumentParser.error() to add suggestions before
    exiting. This catches all parser errors including invalid subcommands and
    invalid options.
    """

    def error(self, message: str) -> None:
        """
        Override error method to add command suggestions.

        Args:
            message: Error message from argparse
        """
        from ..utils import suggest_similar_commands

        # Try to extract the invalid command/option from the error message
        invalid_value = None
        valid_choices = []

        # Handle invalid subcommand errors
        # Format: "argument COMMAND: invalid choice: 'tickts' (choose from ...)"
        if "invalid choice:" in message:
            try:
                # Extract the invalid choice
                parts = message.split("invalid choice: '")
                if len(parts) > 1:
                    invalid_value = parts[1].split("'")[0]

                # Extract valid choices
                if "(choose from" in message:
                    choices_part = message.split("(choose from")[1]
                    # Remove trailing parenthesis and split
                    choices_str = choices_part.rstrip(")")
                    # Parse choices - they may be quoted or unquoted
                    valid_choices = [
                        c.strip().strip("'\"")
                        for c in choices_str.split(",")
                        if c.strip()
                    ]
            except (IndexError, ValueError):
                pass

        # Handle unrecognized arguments (invalid options)
        # Format: "unrecognized arguments: --verbos"
        elif "unrecognized arguments:" in message:
            try:
                parts = message.split("unrecognized arguments:")
                if len(parts) > 1:
                    invalid_value = parts[1].strip().split()[0]

                # Get common options from parser
                valid_choices = []
                for action in self._actions:
                    for option in action.option_strings:
                        valid_choices.append(option)
            except (IndexError, ValueError):
                pass

        # Build error message with suggestions
        from rich.console import Console

        console = Console(stderr=True)

        console.print(f"\n[red]Error:[/red] {message}\n", style="bold")

        # Add suggestions if we found valid choices
        if invalid_value and valid_choices:
            suggestion = suggest_similar_commands(invalid_value, valid_choices)
            if suggestion:
                console.print(f"[yellow]{suggestion}[/yellow]\n")

        # Show help hint
        console.print(f"[dim]Run '{self.prog} --help' for usage information.[/dim]\n")

        # Exit with error code
        sys.exit(2)


def _get_enhanced_version(base_version: str) -> str:
    """
    Get enhanced version string with build number if available.

    Args:
        base_version: Base version string (e.g., "4.0.8")

    Returns:
        Enhanced version string with build number if available
    """
    try:
        # Try to use VersionService for enhanced version display
        from ...services.version_service import VersionService

        version_service = VersionService()
        enhanced = version_service.get_version()

        # If we got an enhanced version (with build number), use it
        # Remove the 'v' prefix since argparse will add the program name
        if enhanced and enhanced.startswith("v"):
            enhanced = enhanced[1:]  # Remove 'v' prefix

        if enhanced and enhanced != base_version:
            return enhanced
    except Exception:
        # If anything fails, fall back to base version
        pass

    return base_version


def add_common_arguments(
    parser: argparse.ArgumentParser, version: Optional[str] = None
) -> None:
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
        # Use enhanced version display with build number if available
        enhanced_version = _get_enhanced_version(version)
        parser.add_argument(
            "--version", action="version", version=f"%(prog)s {enhanced_version}"
        )

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

    DESIGN DECISION: Uses SuggestingArgumentParser to provide helpful suggestions
    for typos and invalid commands, improving user experience.

    Args:
        prog_name: The program name to use
        version: The version string to display

    Returns:
        Configured SuggestingArgumentParser instance ready for subparser addition
    """
    # Main parser with suggestion support
    parser = SuggestingArgumentParser(
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
        "--no-hooks",
        action="store_true",
        help="Disable hook service (runs without hooks)",
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
        "--websocket-port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)",
    )
    run_group.add_argument(
        "--mpm-resume",
        type=str,
        nargs="?",
        const="last",
        help="Resume an MPM session (last session if no ID specified, or specific session ID)",
    )
    run_group.add_argument(
        "--resume",
        action="store_true",
        help="Pass --resume flag to Claude Code to resume the last conversation",
    )
    run_group.add_argument(
        "--force",
        action="store_true",
        help="Force operations even with warnings (e.g., large .claude.json file)",
    )
    run_group.add_argument(
        "--reload-agents",
        action="store_true",
        help="Force rebuild of all system agents by deleting local claude-mpm agents",
    )

    # Dependency checking options (for backward compatibility at top level)
    dep_group_top = parser.add_argument_group(
        "dependency options (when no command specified)"
    )
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
    io_group = parser.add_argument_group(
        "input/output options (when no command specified)"
    )
    io_group.add_argument(
        "-i",
        "--input",
        type=str,
        help="Input text or file path (for non-interactive mode)",
    )
    io_group.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (read from stdin or --input)",
    )


def create_parser(
    prog_name: str = "claude-mpm", version: str = "0.0.0"
) -> argparse.ArgumentParser:
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
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", metavar="COMMAND"
    )

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
        from .source_parser import add_source_subparser

        add_source_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .skill_source_parser import add_skill_source_subparser

        add_skill_source_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .agent_source_parser import add_agent_source_subparser

        add_agent_source_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .auto_configure_parser import add_auto_configure_subparser

        add_auto_configure_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .memory_parser import add_memory_subparser

        add_memory_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .skills_parser import add_skills_subparser

        add_skills_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .config_parser import add_config_subparser

        add_config_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .profile_parser import add_profile_subparser

        add_profile_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .monitor_parser import add_monitor_subparser

        add_monitor_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .dashboard_parser import add_dashboard_subparser

        add_dashboard_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .local_deploy_parser import add_local_deploy_arguments

        add_local_deploy_arguments(subparsers)
    except ImportError:
        pass

    try:
        from .mcp_parser import add_mcp_subparser

        add_mcp_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .agent_manager_parser import add_agent_manager_subparser

        add_agent_manager_subparser(subparsers)
    except ImportError:
        pass

    try:
        from .configure_parser import add_configure_subparser

        add_configure_subparser(subparsers)
    except ImportError:
        pass

    # Add uninstall command parser
    try:
        from ..commands.uninstall import add_uninstall_parser

        add_uninstall_parser(subparsers)
    except ImportError:
        pass

    # Add debug command parser
    try:
        from .debug_parser import add_debug_subparser

        add_debug_subparser(subparsers)
    except ImportError:
        pass

    # Add analyze command parser
    try:
        from .analyze_parser import add_analyze_subparser

        add_analyze_subparser(subparsers)
    except ImportError:
        pass

    # Add analyze-code command parser
    try:
        from .analyze_code_parser import AnalyzeCodeParser

        parser_obj = AnalyzeCodeParser()
        analyze_code_parser = subparsers.add_parser(
            "analyze-code", help=parser_obj.help_text
        )
        parser_obj.add_arguments(analyze_code_parser)
        analyze_code_parser.set_defaults(command="analyze-code")
    except ImportError:
        pass

    # Add mpm-init command parser
    try:
        from .mpm_init_parser import add_mpm_init_subparser

        add_mpm_init_subparser(subparsers)
    except ImportError:
        pass

    # Add search command parser
    try:
        from .search_parser import add_search_subparser

        add_search_subparser(subparsers)
    except ImportError:
        pass

    # Import and add additional command parsers from commands module
    try:
        from ..commands.aggregate import add_aggregate_parser

        add_aggregate_parser(subparsers)

        from ..commands.cleanup import add_cleanup_parser

        add_cleanup_parser(subparsers)

        # MCP pipx configuration command
        if hasattr(CLICommands, "MCP_PIPX_CONFIG") or True:  # Always add for now
            from ..commands.mcp_pipx_config import add_parser as add_mcp_pipx_parser

            add_mcp_pipx_parser(subparsers)

        from ..commands.doctor import add_doctor_parser

        add_doctor_parser(subparsers)

        from ..commands.postmortem import add_postmortem_parser

        add_postmortem_parser(subparsers)

        # Add upgrade command
        from ..commands.upgrade import add_upgrade_parser

        add_upgrade_parser(subparsers)

        # Add verify command for MCP service verification
        from ..commands.verify import add_parser as add_verify_parser

        add_verify_parser(subparsers)

        # Add hook-errors command for managing hook error memory
        hook_errors_parser = subparsers.add_parser(
            "hook-errors",
            help="Manage hook error memory and diagnostics",
        )
        hook_errors_parser.add_argument(
            "hook_errors_command",
            nargs="?",
            choices=["list", "summary", "clear", "diagnose", "status"],
            help="Hook errors subcommand",
        )
        hook_errors_parser.add_argument(
            "--format",
            choices=["table", "json"],
            default="table",
            help="Output format for list command",
        )
        hook_errors_parser.add_argument(
            "--hook-type",
            help="Filter by specific hook type",
        )
        hook_errors_parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            help="Skip confirmation prompts",
        )

        # Add summarize command
        from ..commands.summarize import add_summarize_parser

        add_summarize_parser(subparsers)
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
