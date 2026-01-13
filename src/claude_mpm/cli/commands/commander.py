"""CLI commands for Commander daemon."""

import asyncio
import logging
import sys
from argparse import Namespace
from pathlib import Path

from claude_mpm.commander import DaemonConfig

logger = logging.getLogger(__name__)


def handle_commander_start(args: Namespace) -> int:
    """Handle 'commander start' command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Build daemon config from args
        config = DaemonConfig(
            host=getattr(args, "host", "127.0.0.1"),
            port=getattr(args, "port", 8765),
            log_level=getattr(args, "log_level", "INFO"),
        )

        # Override state_dir if provided
        if hasattr(args, "state_dir") and args.state_dir:
            config.state_dir = Path(args.state_dir)

        print(f"Starting Commander daemon on {config.host}:{config.port}")
        print(f"State directory: {config.state_dir}")
        print("Press Ctrl+C to stop")
        print()

        # Run daemon
        asyncio.run(_run_daemon(config))

        return 0

    except KeyboardInterrupt:
        print("\nShutdown complete")
        return 0
    except Exception as e:
        logger.error(f"Failed to start daemon: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def _run_daemon(config: DaemonConfig) -> None:
    """Run daemon asynchronously.

    Args:
        config: Daemon configuration
    """
    from claude_mpm.commander.daemon import main

    await main(config)


def handle_commander_stop(args: Namespace) -> int:
    """Handle 'commander stop' command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # TODO: Implement graceful shutdown via API or signal
        # For now, just inform user to use Ctrl+C
        print("To stop the daemon, use Ctrl+C in the terminal where it's running")
        print("Or send SIGTERM to the daemon process")
        return 0

    except Exception as e:
        logger.error(f"Failed to stop daemon: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_commander_status(args: Namespace) -> int:
    """Handle 'commander status' command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        import requests

        port = getattr(args, "port", 8765)
        url = f"http://127.0.0.1:{port}/api/health"

        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                print("Commander daemon is running")
                print(f"  Status: {data.get('status', 'unknown')}")
                print(f"  Version: {data.get('version', 'unknown')}")
                return 0
            print(f"Commander daemon responded with status {response.status_code}")
            return 1

        except requests.exceptions.RequestException:
            print("Commander daemon is not running")
            print(f"  (checked {url})")
            return 1

    except Exception as e:
        logger.error(f"Failed to check status: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


def add_commander_subparsers(subparsers) -> None:
    """Add commander subcommands to argument parser.

    Args:
        subparsers: Subparser action from ArgumentParser
    """
    # Commander parent command
    commander_parser = subparsers.add_parser(
        "commander",
        help="Manage Commander daemon for multi-project orchestration",
    )

    commander_subparsers = commander_parser.add_subparsers(
        dest="commander_action",
        help="Commander action",
    )

    # commander start
    start_parser = commander_subparsers.add_parser(
        "start",
        help="Start Commander daemon",
    )
    start_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="API server bind address (default: 127.0.0.1)",
    )
    start_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="API server port (default: 8765)",
    )
    start_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    start_parser.add_argument(
        "--state-dir",
        type=Path,
        help="State persistence directory (default: ~/.claude-mpm/commander)",
    )

    # commander stop
    commander_subparsers.add_parser(
        "stop",
        help="Stop Commander daemon",
    )

    # commander status
    status_parser = commander_subparsers.add_parser(
        "status",
        help="Check Commander daemon status",
    )
    status_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="API server port (default: 8765)",
    )


def handle_commander_command(args: Namespace) -> int:
    """Route commander commands to appropriate handlers.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    action = getattr(args, "commander_action", None)

    if action == "start":
        return handle_commander_start(args)
    if action == "stop":
        return handle_commander_stop(args)
    if action == "status":
        return handle_commander_status(args)
    print("Usage: claude-mpm commander {start|stop|status}")
    print("Run 'claude-mpm commander --help' for more information")
    return 1
