#!/usr/bin/env python3
"""
Launch Monitor Script for Claude MPM.

This script provides the entry point for launching the Claude MPM monitor
dashboard, which includes both the Socket.IO server and web interface.

WHY: Provides a simple command to start the monitoring dashboard that tracks
Claude MPM events and agent activity in real-time.

SINGLE INSTANCE ENFORCEMENT:
- Only ONE monitor instance runs at a time on port 8765 (default)
- If monitor already running on default port: reuse existing, open browser
- If user specifies --port explicitly: use that port, fail if busy
- No auto-increment port selection (prevents multiple instances)
"""

import argparse
import sys
import webbrowser

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.monitor.daemon import UnifiedMonitorDaemon
from claude_mpm.services.monitor.daemon_manager import DaemonManager

DEFAULT_PORT = 8765
logger = get_logger(__name__)


def check_existing_monitor(host: str, port: int) -> bool:
    """Check if monitor is already running on the specified port.

    Args:
        host: Host to check
        port: Port to check

    Returns:
        True if monitor is running, False otherwise
    """
    try:
        import requests

        response = requests.get(f"http://{host}:{port}/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            # Check if it's our claude-mpm-monitor service
            if data.get("service") == "claude-mpm-monitor":
                return True
    except Exception:
        pass
    return False


def main():
    """Main entry point for monitor launcher."""
    parser = argparse.ArgumentParser(
        description="Launch Claude MPM monitoring dashboard"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,  # Changed: None means use DEFAULT_PORT with single-instance check
        help=f"Port to run on (default: {DEFAULT_PORT}). If specified, fails if port is busy.",
    )

    parser.add_argument(
        "--host", default="localhost", help="Host to bind to (default: localhost)"
    )

    parser.add_argument(
        "--no-browser", action="store_true", help="Do not open browser automatically"
    )

    parser.add_argument(
        "--background", action="store_true", help="Run in background daemon mode"
    )

    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable development mode with hot reload for Svelte changes",
    )

    args = parser.parse_args()

    # Determine target port
    user_specified_port = args.port is not None
    target_port = args.port if user_specified_port else DEFAULT_PORT

    # SINGLE INSTANCE ENFORCEMENT:
    # Check if monitor already running on target port
    if check_existing_monitor(args.host, target_port):
        logger.info(f"Monitor already running at http://{args.host}:{target_port}")

        # Open browser to existing instance if requested
        if not args.no_browser:
            url = f"http://{args.host}:{target_port}"
            logger.info(f"Opening browser to existing instance: {url}")
            webbrowser.open(url)

        # Success - reusing existing instance
        return

    # Port selection logic:
    # - If user specified --port: Use that exact port, fail if busy
    # - If no --port: Use DEFAULT_PORT (8765), fail if busy
    # - Never auto-increment to find free port

    # Create daemon manager for port checking
    daemon_manager = DaemonManager(port=target_port, host=args.host)

    if not daemon_manager._is_port_available():
        if user_specified_port:
            # User explicitly requested a port - fail with clear message
            logger.error(
                f"Port {target_port} is already in use by another service. "
                f"Please stop the existing service or choose a different port."
            )
            sys.exit(1)
        else:
            # Default port is busy - fail with helpful message
            logger.error(
                f"Default port {DEFAULT_PORT} is already in use by another service. "
                f"Please stop the existing service with 'claude-mpm monitor stop' "
                f"or specify a different port with --port."
            )
            sys.exit(1)

    # Start the monitor daemon
    if args.dev:
        logger.info(
            f"Starting Claude MPM monitor on {args.host}:{target_port} (DEV MODE - hot reload enabled)"
        )
    else:
        logger.info(f"Starting Claude MPM monitor on {args.host}:{target_port}")

    daemon = UnifiedMonitorDaemon(
        host=args.host,
        port=target_port,
        daemon_mode=args.background,
        enable_hot_reload=args.dev,
    )

    success = daemon.start()

    if success:
        # Open browser if requested
        if not args.no_browser:
            url = f"http://{args.host}:{target_port}"
            logger.info(f"Opening browser to {url}")
            webbrowser.open(url)

        if args.background:
            logger.info(f"Monitor daemon started in background on port {target_port}")
        else:
            logger.info(f"Monitor running on port {target_port}")
            logger.info("Press Ctrl+C to stop")
    else:
        logger.error("Failed to start monitor")
        sys.exit(1)


if __name__ == "__main__":
    main()
