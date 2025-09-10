from pathlib import Path
from typing import Optional

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

from claude_mpm.config.paths import paths

from ..constants import CLICommands, LogLevel
from .commands import (  # run_guarded_session is imported lazily to avoid loading experimental code
    aggregate_command,
    cleanup_memory,
    manage_agent_manager,
    manage_agents,
    manage_config,
    manage_configure,
    manage_debug,
    manage_mcp,
    manage_memory,
    manage_monitor,
    manage_tickets,
    run_doctor,
    run_session,
    show_info,
)
from .commands.analyze_code import manage_analyze_code
from .commands.dashboard import manage_dashboard
from .parser import create_parser, preprocess_args
from .utils import ensure_directories, setup_logging

# Get version using centralized path management
# Try package VERSION file first (for installed packages)
package_version_file = Path(__file__).parent.parent / "VERSION"
if package_version_file.exists():
    __version__ = package_version_file.read_text().strip()
# Use centralized path management for VERSION file
elif paths.version_file.exists():
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
    # Disable telemetry by default (set early in case any imported modules check it)
    import os

    os.environ.setdefault("DISABLE_TELEMETRY", "1")

    # Ensure directories are initialized on first run
    ensure_directories()

    # Initialize or update project registry
    _initialize_project_registry()

    # Parse args early to check if we should skip auto-configuration
    # (for commands like --version, --help, etc.)
    parser = create_parser(version=__version__)
    processed_argv = preprocess_args(argv)
    args = parser.parse_args(processed_argv)

    # Skip auto-configuration for certain commands
    skip_auto_config_commands = ["--version", "-v", "--help", "-h"]
    # sys is already imported at module level (line 16), use it directly
    should_skip_auto_config = any(
        cmd in (processed_argv or sys.argv[1:]) for cmd in skip_auto_config_commands
    ) or (
        hasattr(args, "command") and args.command in ["info", "doctor", "config", "mcp"]
    )  # Info, diagnostic, and MCP commands

    if not should_skip_auto_config:
        # Check for MCP auto-configuration (pipx installations)
        _check_mcp_auto_configuration()

    # DISABLED: MCP pre-warming causes fork() issues with monitor daemon (v4.2.39)
    # The pre-warming creates background threads that interfere with the monitor's
    # daemonization process, causing race conditions and port binding errors.
    # Accepting the 11.9s delay on first MCP use is better than a broken monitor.
    # _verify_mcp_gateway_startup()

    # Set up logging
    # Special case: For MCP start command, we need minimal logging to avoid stdout interference
    if (
        args.command == CLICommands.MCP.value
        and getattr(args, "mcp_command", None) == "start"
    ):
        # For MCP server, configure minimal stderr-only logging
        import logging

        # sys is already imported at module level
        # Only log errors to stderr for MCP server
        if not getattr(args, "test", False) and not getattr(
            args, "instructions", False
        ):
            # Production MCP mode - minimal logging
            logging.basicConfig(
                level=logging.ERROR, format="%(message)s", stream=sys.stderr, force=True
            )
            logger = logging.getLogger("claude_mpm")
        else:
            # Test or instructions mode - normal logging
            logger = setup_logging(args)
    else:
        # Normal logging for all other commands
        logger = setup_logging(args)

    # Debug output if requested
    if hasattr(args, "debug") and args.debug:
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
        return _execute_command(args.command, args)
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
        from ..services.project.registry import ProjectRegistry

        registry = ProjectRegistry()
        registry.get_or_create_project_entry()
    except Exception as e:
        # Import logger here to avoid circular imports
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to initialize project registry: {e}")
        # Continue execution - registry failure shouldn't block startup


def _check_mcp_auto_configuration():
    """
    Check and potentially auto-configure MCP for pipx installations.

    WHY: Users installing via pipx should have MCP work out-of-the-box with
    minimal friction. This function offers one-time auto-configuration with
    user consent.

    DESIGN DECISION: This is blocking but quick - it only runs once and has
    a 10-second timeout. We want to catch users on first run for the best
    experience.
    """
    try:
        from ..services.mcp_gateway.auto_configure import check_and_configure_mcp

        # This function handles all the logic:
        # - Checks if already configured
        # - Checks if pipx installation
        # - Checks if already asked before
        # - Prompts user if needed
        # - Configures if user agrees
        check_and_configure_mcp()

    except Exception as e:
        # Non-critical - log but don't fail
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"MCP auto-configuration check failed: {e}")


def _verify_mcp_gateway_startup():
    """
    Verify MCP Gateway configuration on startup and pre-warm MCP services.

    WHY: The MCP gateway should be automatically configured and verified on startup
    to provide a seamless experience with diagnostic tools, file summarizer, and
    ticket service. Pre-warming MCP services eliminates the 11.9s delay on first use.

    DESIGN DECISION: This is non-blocking - failures are logged but don't prevent
    startup to ensure claude-mpm remains functional even if MCP gateway has issues.
    """
    try:
        import asyncio
        import time

        from ..core.logger import get_logger
        from ..services.mcp_gateway.core.process_pool import pre_warm_mcp_servers
        from ..services.mcp_gateway.core.startup_verification import (
            is_mcp_gateway_configured,
            verify_mcp_gateway_on_startup,
        )

        logger = get_logger("mcp_prewarm")

        # Quick check first - if already configured, skip detailed verification
        gateway_configured = is_mcp_gateway_configured()

        # Pre-warm MCP servers regardless of gateway config
        # This eliminates the 11.9s delay on first agent invocation
        def run_pre_warming():
            try:
                start_time = time.time()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Pre-warm MCP servers (especially vector search)
                logger.info("Pre-warming MCP servers to eliminate startup delay...")
                loop.run_until_complete(pre_warm_mcp_servers())

                pre_warm_time = time.time() - start_time
                if pre_warm_time > 1.0:
                    logger.info(f"MCP servers pre-warmed in {pre_warm_time:.2f}s")

                # Also run gateway verification if needed
                if not gateway_configured:
                    loop.run_until_complete(verify_mcp_gateway_on_startup())

                loop.close()
            except Exception as e:
                # Non-blocking - log but don't fail
                logger.debug(f"MCP pre-warming error (non-critical): {e}")

        # Run pre-warming in background thread
        import threading

        pre_warm_thread = threading.Thread(target=run_pre_warming, daemon=True)
        pre_warm_thread.start()

        return

        # Run detailed verification in background if not configured
        if not gateway_configured:
            # Note: We don't await this to avoid blocking startup
            def run_verification():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(verify_mcp_gateway_on_startup())
                    loop.close()

                    # Log results but don't block
                    from ..core.logger import get_logger

                    logger = get_logger("cli")

                    if results.get("gateway_configured"):
                        logger.debug("MCP Gateway verification completed successfully")
                    else:
                        logger.debug("MCP Gateway verification completed with warnings")

                except Exception as e:
                    from ..core.logger import get_logger

                    logger = get_logger("cli")
                    logger.debug(f"MCP Gateway verification failed: {e}")

            # Run in background thread to avoid blocking startup
            import threading

            verification_thread = threading.Thread(target=run_verification, daemon=True)
            verification_thread.start()

    except Exception as e:
        # Import logger here to avoid circular imports
        from ..core.logger import get_logger

        logger = get_logger("cli")
        logger.debug(f"Failed to start MCP Gateway verification: {e}")
        # Continue execution - MCP gateway issues shouldn't block startup


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
    args.no_tickets = getattr(args, "no_tickets", False)
    args.no_hooks = getattr(args, "no_hooks", False)
    args.intercept_commands = getattr(args, "intercept_commands", False)
    args.input = getattr(args, "input", None)
    args.non_interactive = getattr(args, "non_interactive", False)
    args.no_native_agents = getattr(args, "no_native_agents", False)

    # Handle claude_args - if --resume flag is set, add it to claude_args
    claude_args = getattr(args, "claude_args", [])
    if getattr(args, "resume", False):
        # Add --resume to claude_args if not already present
        if "--resume" not in claude_args:
            claude_args = ["--resume", *claude_args]
    args.claude_args = claude_args

    args.launch_method = getattr(args, "launch_method", "exec")
    args.websocket = getattr(args, "websocket", False)
    args.websocket_port = getattr(args, "websocket_port", 8765)
    # CRITICAL: Include mpm_resume attribute for session resumption
    args.mpm_resume = getattr(args, "mpm_resume", None)
    # Also include monitor and force attributes
    args.monitor = getattr(args, "monitor", False)
    args.force = getattr(args, "force", False)
    # Include dependency checking attributes
    args.check_dependencies = getattr(args, "check_dependencies", True)
    args.force_check_dependencies = getattr(args, "force_check_dependencies", False)
    args.no_prompt = getattr(args, "no_prompt", False)
    args.force_prompt = getattr(args, "force_prompt", False)


def _execute_command(command: str, args) -> int:
    """
    Execute the specified command.

    WHY: This function maps command names to their implementations, providing
    a single place to manage command routing. Experimental commands are imported
    lazily to avoid loading unnecessary code.

    DESIGN DECISION: run_guarded is imported only when needed to maintain
    separation between stable and experimental features.

    Args:
        command: The command name to execute
        args: Parsed command line arguments

    Returns:
        Exit code from the command
    """
    # Handle experimental run-guarded command separately with lazy import
    if command == "run-guarded":
        # Lazy import to avoid loading experimental code unless needed
        from .commands.run_guarded import execute_run_guarded

        result = execute_run_guarded(args)
        return result if result is not None else 0

    # Handle mpm-init command with lazy import
    if command == "mpm-init":
        # Lazy import to avoid loading unless needed
        from .commands.mpm_init_handler import manage_mpm_init

        result = manage_mpm_init(args)
        return result if result is not None else 0

    # Handle uninstall command with lazy import
    if command == "uninstall":
        # Lazy import to avoid loading unless needed
        from .commands.uninstall import UninstallCommand

        cmd = UninstallCommand()
        result = cmd.execute(args)
        # Convert CommandResult to exit code
        return result.exit_code if result else 0

    # Map stable commands to their implementations
    command_map = {
        CLICommands.RUN.value: run_session,
        # CLICommands.RUN_GUARDED.value is handled above
        CLICommands.TICKETS.value: manage_tickets,
        CLICommands.INFO.value: show_info,
        CLICommands.AGENTS.value: manage_agents,
        CLICommands.AGENT_MANAGER.value: manage_agent_manager,
        CLICommands.MEMORY.value: manage_memory,
        CLICommands.MONITOR.value: manage_monitor,
        CLICommands.DASHBOARD.value: manage_dashboard,
        CLICommands.CONFIG.value: manage_config,
        CLICommands.CONFIGURE.value: manage_configure,
        CLICommands.AGGREGATE.value: aggregate_command,
        CLICommands.ANALYZE_CODE.value: manage_analyze_code,
        CLICommands.CLEANUP.value: cleanup_memory,
        CLICommands.MCP.value: manage_mcp,
        CLICommands.DOCTOR.value: run_doctor,
        "debug": manage_debug,  # Add debug command
        "mpm-init": None,  # Will be handled separately with lazy import
    }

    # Execute command if found
    if command in command_map:
        result = command_map[command](args)
        # Commands may return None (success) or an exit code
        return result if result is not None else 0
    # Unknown command - this shouldn't happen with argparse
    # but we handle it for completeness
    print(f"Unknown command: {command}")
    return 1


# For backward compatibility - export main
if __name__ == "__main__":
    sys.exit(main())
