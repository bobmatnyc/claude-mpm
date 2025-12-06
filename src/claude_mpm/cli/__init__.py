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

from claude_mpm.config.paths import paths

from ..constants import CLICommands
from ..utils.progress import ProgressBar
from .executor import ensure_run_attributes, execute_command
from .helpers import (
    handle_missing_configuration,
    has_configuration_file,
    should_skip_config_check,
)
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
package_version_file = Path(__file__).parent.parent / "VERSION"
if package_version_file.exists():
    __version__ = package_version_file.read_text().strip()
elif paths.version_file.exists():
    __version__ = paths.version_file.read_text().strip()
else:
    try:
        from .. import __version__
    except ImportError:
        __version__ = "0.0.0"


def main(argv: Optional[list] = None):
    """Main CLI entry point orchestrating argument parsing and command execution."""
    argv = setup_early_environment(argv)

    parser = create_parser(version=__version__)
    processed_argv = preprocess_args(argv)
    args = parser.parse_args(processed_argv)

    help_version_flags = ["--version", "-v", "--help", "-h"]
    is_help_or_version = any(
        flag in (processed_argv or sys.argv[1:]) for flag in help_version_flags
    )

    if not has_configuration_file() and not is_help_or_version:
        if not should_skip_config_check(getattr(args, "command", None)):
            handle_missing_configuration()

    setup_configure_command_environment(args)

    # CRITICAL: Setup logging BEFORE any initialization that creates loggers
    # This ensures that ensure_directories() and run_background_services()
    # respect the user's logging preference (default: OFF)
    logger = setup_mcp_server_logging(args)

    ensure_directories()

    # Display startup banner FIRST (unless help/version/utility commands)
    if should_show_banner(args):
        logging_level = getattr(args, "logging", "OFF")
        display_startup_banner(__version__, logging_level)

    if not should_skip_background_services(args, processed_argv):
        # Show "Launching Claude..." progress bar during background services startup
        # This matches the visual style of agent/skill sync progress bars
        launch_progress = ProgressBar(
            total=100,
            prefix="Launching Claude",
            show_percentage=False,
            show_counter=False,
            bar_width=25,
        )

        try:
            run_background_services()
            launch_progress.finish(message="Ready")

            # Inform user about Claude Code initialization delay (3-5 seconds)
            # This message appears before os.execvpe() replaces our process
            # See: docs/research/claude-startup-delay-analysis-2025-12-01.md
            print(
                "⏳ Starting Claude Code... (this may take a few seconds)",
                flush=True,
            )
        except Exception:
            launch_progress.finish(message="Failed")
            raise

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
