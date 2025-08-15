"""
Claude MPM Command-Line Interface.

WHY: This module serves as the main entry point for the CLI, coordinating
argument parsing and command execution. It replaces the monolithic cli.py
with a more modular structure.

DESIGN DECISION: We maintain backward compatibility by keeping the same
interface while organizing code into logical modules. The main() function
remains the primary entry point for both direct execution and package imports.
"""

import sys
from pathlib import Path
from typing import Optional

from ..constants import CLICommands, LogLevel
from .parser import create_parser, preprocess_args
from .utils import ensure_directories, setup_logging
from .commands import (
    run_session,
    manage_tickets,
    show_info,
    manage_agents,
    manage_memory,
    manage_monitor,
    manage_config,
    aggregate_command,
    cleanup_memory
)
from claude_mpm.config.paths import paths

# Get version using centralized path management
# Try package VERSION file first (for installed packages)
package_version_file = Path(__file__).parent.parent / "VERSION"
if package_version_file.exists():
    __version__ = package_version_file.read_text().strip()
else:
    # Use centralized path management for VERSION file
    if paths.version_file.exists():
        __version__ = paths.version_file.read_text().strip()
    else:
        # Try to import from package as fallback
        try:
            from .. import __version__
        except ImportError:
            # Default version if all else fails
            __version__ = "0.0.0"


def main(argv: Optional[list] = None):
    """
    Main CLI entry point.
    
    WHY: This function orchestrates the entire CLI flow:
    1. Ensures directories exist
    2. Preprocesses arguments (handling --mpm: prefix)
    3. Parses arguments
    4. Sets up logging
    5. Executes the appropriate command
    
    DESIGN DECISION: We keep error handling at this level to provide consistent
    error messages and exit codes across all commands.
    
    Args:
        argv: Optional list of command line arguments for testing
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    # Ensure directories are initialized on first run
    ensure_directories()
    
    # Initialize or update project registry
    _initialize_project_registry()
    
    # Create parser with version
    parser = create_parser(version=__version__)
    
    # Preprocess and parse arguments
    processed_argv = preprocess_args(argv)
    args = parser.parse_args(processed_argv)
    
    # Set up logging
    logger = setup_logging(args)
    
    # Debug output if requested
    if hasattr(args, 'debug') and args.debug:
        logger.debug(f"Command: {args.command}")
        logger.debug(f"Arguments: {args}")
    
    # Hook system note: Claude Code hooks are handled externally via the
    # hook_handler.py script installed in ~/.claude/settings.json
    # The --no-hooks flag is kept for backward compatibility but doesn't affect
    # Claude Code hooks which are configured separately.
    
    # Default to run command if no command specified
    if not args.command:
        args.command = CLICommands.RUN.value
        # Ensure run-specific attributes exist when defaulting to run
        _ensure_run_attributes(args)
    
    # Execute command
    try:
        exit_code = _execute_command(args.command, args)
        return exit_code
    except KeyboardInterrupt:
        logger.info("Session interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def _initialize_project_registry():
    """
    Initialize or update the project registry for the current session.
    
    WHY: The project registry tracks all claude-mpm projects and their metadata
    across sessions. This function ensures the current project is properly
    registered and updates session information.
    
    DESIGN DECISION: Registry failures are logged but don't prevent startup
    to ensure claude-mpm remains functional even if registry operations fail.
    """
    try:
        from ..services.project_registry import ProjectRegistry
        registry = ProjectRegistry()
        registry.get_or_create_project_entry()
    except Exception as e:
        # Import logger here to avoid circular imports
        from ..core.logger import get_logger
        logger = get_logger("cli")
        logger.debug(f"Failed to initialize project registry: {e}")
        # Continue execution - registry failure shouldn't block startup


def _ensure_run_attributes(args):
    """
    Ensure run command attributes exist when defaulting to run.
    
    WHY: When no command is specified, we default to 'run' but the args object
    won't have run-specific attributes from the subparser. This function ensures
    they exist with sensible defaults.
    
    Args:
        args: Parsed arguments object to update
    """
    # Set defaults for run command attributes
    args.no_tickets = getattr(args, 'no_tickets', False)
    args.no_hooks = getattr(args, 'no_hooks', False)
    args.intercept_commands = getattr(args, 'intercept_commands', False)
    args.input = getattr(args, 'input', None)
    args.non_interactive = getattr(args, 'non_interactive', False)
    args.no_native_agents = getattr(args, 'no_native_agents', False)
    args.claude_args = getattr(args, 'claude_args', [])
    args.launch_method = getattr(args, 'launch_method', 'exec')
    args.websocket = getattr(args, 'websocket', False)
    args.websocket_port = getattr(args, 'websocket_port', 8765)


def _execute_command(command: str, args) -> int:
    """
    Execute the specified command.
    
    WHY: This function maps command names to their implementations, providing
    a single place to manage command routing.
    
    Args:
        command: The command name to execute
        args: Parsed command line arguments
        
    Returns:
        Exit code from the command
    """
    # Map commands to their implementations
    command_map = {
        CLICommands.RUN.value: run_session,
        CLICommands.TICKETS.value: manage_tickets,
        CLICommands.INFO.value: show_info,
        CLICommands.AGENTS.value: manage_agents,
        CLICommands.MEMORY.value: manage_memory,
        CLICommands.MONITOR.value: manage_monitor,
        CLICommands.CONFIG.value: manage_config,
        CLICommands.AGGREGATE.value: aggregate_command,
        CLICommands.CLEANUP.value: cleanup_memory,
    }
    
    # Execute command if found
    if command in command_map:
        result = command_map[command](args)
        # Commands may return None (success) or an exit code
        return result if result is not None else 0
    else:
        # Unknown command - this shouldn't happen with argparse
        # but we handle it for completeness
        print(f"Unknown command: {command}")
        return 1


# For backward compatibility - export main
if __name__ == "__main__":
    sys.exit(main())