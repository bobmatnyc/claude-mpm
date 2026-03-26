"""
Claude MPM Command-Line Interface.

Main entry point for CLI. Implementation details extracted to:
- cli/helpers.py: Configuration checks and prompts
- cli/startup.py: Initialization (registry, MCP, updates)
- cli/executor.py: Command execution routing

Refactored from 803 lines to <130 lines (TSK-0053).
"""

import os
import sys
from pathlib import Path
from typing import Optional

from ..constants import CLICommands
from ..utils.progress import ProgressBar, StartupProgressBar
from .executor import ensure_run_attributes, execute_command

# handle_missing_configuration, has_configuration_file, should_skip_config_check
# removed - startup config prompt disabled, users can run `/mpm-configure` manually
from .parser import create_parser, preprocess_args
from .startup import (
    run_background_services,
    setup_configure_command_environment,
    setup_early_environment,
    setup_mcp_server_logging,
    should_skip_background_services,
)
from .startup_display import display_startup_banner, should_show_banner
from .utils import ensure_directories, setup_logging

# Version resolution
# CRITICAL: Don't import 'paths' here - it triggers UnifiedPathManager initialization
# before setup_early_environment() can set CLAUDE_MPM_USER_PWD
package_version_file = Path(__file__).parent.parent / "VERSION"
if package_version_file.exists():
    __version__ = package_version_file.read_text().strip()
else:
    try:
        from .. import __version__
    except ImportError:
        __version__ = "0.0.0"


def main(argv: list | None = None):
    """Main CLI entry point orchestrating argument parsing and command execution."""
    argv = setup_early_environment(argv)

    parser = create_parser(version=__version__)
    processed_argv = preprocess_args(argv)
    args = parser.parse_args(processed_argv)

    # Configuration prompt removed - users can run `/mpm-configure` manually
    # See: handle_missing_configuration() in helpers.py if re-enabling
    # if not has_configuration_file() and not is_help_or_version:
    #     if not should_skip_config_check(getattr(args, "command", None)):
    #         handle_missing_configuration()

    setup_configure_command_environment(args)

    # CRITICAL: Setup logging BEFORE any initialization that creates loggers
    # This ensures that ensure_directories() and run_background_services()
    # respect the user's logging preference (default: OFF)
    logger = setup_mcp_server_logging(args)

    ensure_directories()

    # Run migrations BEFORE banner (so we can show results in banner)
    # Migrations are quick and non-blocking, safe to run early
    applied_migrations: list[str] = []
    if not should_skip_background_services(args, processed_argv):
        from .startup_migrations import run_migrations

        applied_migrations = run_migrations()

    # Display startup banner (unless help/version/utility commands)
    # Pass migration results so they appear in banner only when applicable
    if should_show_banner(args):
        logging_level = getattr(args, "logging", "OFF")
        display_startup_banner(__version__, logging_level, applied_migrations)

        # Show runtime mode if explicitly selected via --sdk or --cli
        use_sdk = getattr(args, "sdk", False)
        use_cli = getattr(args, "cli", False)
        if use_sdk:
            logger.info("Runtime: sdk")
        elif use_cli:
            logger.info("Runtime: cli")

    # Check for --inject-port flag to start injection endpoint
    # (outside background services block — always start if requested)
    inject_port = getattr(args, "inject_port", None)
    if inject_port is not None:
        os.environ["CLAUDE_MPM_INJECT_PORT"] = str(inject_port)
        import threading

        from ..services.agents.message_endpoint import MessageEndpoint

        endpoint = MessageEndpoint(port=inject_port)
        thread = threading.Thread(target=endpoint.run, daemon=True)
        thread.start()

        # Register shutdown handler for clean port release
        import atexit

        atexit.register(endpoint.shutdown)
        logger.info(f"Message injection endpoint started on port {inject_port}")

    if not should_skip_background_services(args, processed_argv):
        # Check for --force-sync flag or environment variable
        force_sync = getattr(args, "force_sync", False) or os.environ.get(
            "CLAUDE_MPM_FORCE_SYNC", "0"
        ) in ("1", "true", "True", "yes")

        # Check for --no-sync flag or environment variable
        no_sync = getattr(args, "no_sync", False) or os.environ.get(
            "CLAUDE_MPM_NO_SYNC", "0"
        ) in ("1", "true", "True", "yes")

        # Check for --skip-compat-check flag or environment variable
        skip_compat_check = getattr(args, "skip_compat_check", False) or os.environ.get(
            "CLAUDE_MPM_SKIP_COMPAT_CHECK", "0"
        ) in ("1", "true", "True", "yes")

        # Propagate CLI flag to env var so it reaches _check_manifest_compatibility
        # (which checks the env var directly, avoiding the need to thread the flag
        # through all intermediate startup functions)
        if skip_compat_check:
            os.environ["CLAUDE_MPM_SKIP_COMPAT_CHECK"] = "1"

        # Check for --sdk / --cli flags to select runtime
        use_sdk = getattr(args, "sdk", False)
        if use_sdk:
            os.environ["CLAUDE_MPM_RUNTIME"] = "sdk"

        use_cli = getattr(args, "cli", False)
        if use_cli:
            os.environ["CLAUDE_MPM_RUNTIME"] = "cli"

        # Check if running in headless mode
        is_headless = getattr(args, "headless", False)

        if is_headless:
            # Headless mode: Run services quietly (stdout -> stderr)
            # No progress bar - stdout must stay clean for JSON streaming
            run_background_services(
                force_sync=force_sync, headless=True, no_sync=no_sync
            )
        else:
            # Normal mode: Show single-line startup progress bar.
            # StartupProgressBar suppresses sub-step stdout while active,
            # then clears itself so Claude's output starts on a clean line.
            _startup_steps = [
                "Syncing hooks & agents",
                "Loading project registry",
                "Checking MCP config",
                "Starting MCP gateway",
                "Checking for updates",
                "Loading skills",
                "Syncing remote skills",
                "Discovering skills",
                "Building domain skills",
                "Verifying PM skills",
                "Configuring output",
                "Setting up browser tools",
            ]
            with StartupProgressBar(
                steps=_startup_steps,
                title="Loading claude-mpm",
            ) as startup_pb:
                run_background_services(
                    force_sync=force_sync,
                    headless=False,
                    no_sync=no_sync,
                    progress=startup_pb,
                )
            # Progress bar cleared on __exit__; now show the "starting" notice
            # Inform user about Claude Code initialization delay (3-5 seconds)
            # This message appears before os.execvpe() replaces our process
            # See: docs/research/claude-startup-delay-analysis-2025-12-01.md
            print(
                "⏳ Starting Claude Code... (this may take a few seconds)",
                flush=True,
            )

    if hasattr(args, "debug") and args.debug:
        logger.debug(f"Command: {args.command}")
        logger.debug(f"Arguments: {args}")

    if not args.command:
        args.command = CLICommands.RUN.value
        ensure_run_attributes(args)

    try:
        return execute_command(args.command, args)
    except KeyboardInterrupt:
        logger.info("Session interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1


# For backward compatibility - export main
if __name__ == "__main__":
    sys.exit(main())
