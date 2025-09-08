#!/usr/bin/env python3
"""
Launch Monitor Script for Claude MPM.

This script provides the entry point for launching the Claude MPM monitor
dashboard, which includes both the Socket.IO server and web interface.

WHY: Provides a simple command to start the monitoring dashboard that tracks
Claude MPM events and agent activity in real-time.
"""

import argparse
import sys
import webbrowser

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.monitor.daemon import UnifiedMonitorDaemon
from claude_mpm.services.port_manager import PortManager

DEFAULT_PORT = 8765
logger = get_logger(__name__)


def main():
    """Main entry point for monitor launcher."""
    parser = argparse.ArgumentParser(
        description="Launch Claude MPM monitoring dashboard"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to run on (default: {DEFAULT_PORT})",
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

    args = parser.parse_args()

    # Find available port
    port_manager = PortManager()
    actual_port = port_manager.find_available_port(preferred_port=args.port)

    if actual_port != args.port:
        logger.info(f"Port {args.port} is in use, using port {actual_port} instead")

    # Start the monitor daemon
    logger.info(f"Starting Claude MPM monitor on {args.host}:{actual_port}")

    daemon = UnifiedMonitorDaemon(
        host=args.host, port=actual_port, daemon_mode=args.background
    )

    success = daemon.start()

    if success:
        # Open browser if requested
        if not args.no_browser:
            url = f"http://{args.host}:{actual_port}"
            logger.info(f"Opening browser to {url}")
            webbrowser.open(url)

        if args.background:
            logger.info(f"Monitor daemon started in background on port {actual_port}")
        else:
            logger.info(f"Monitor running on port {actual_port}")
            logger.info("Press Ctrl+C to stop")
    else:
        logger.error("Failed to start monitor")
        sys.exit(1)


if __name__ == "__main__":
    main()
