#!/usr/bin/env python3
"""Simple monitor launcher for Claude MPM.

WHY: This script provides a streamlined solution for opening the static HTML
monitor that connects to any Socket.IO server. It eliminates server confusion
by separating the monitor client from the server.

DESIGN DECISION: Uses a static HTML file that can be opened directly in
the browser, connecting to whatever Socket.IO server is running. This
eliminates all confusion about which server serves what.

The script handles:
1. Opening the static HTML file in browser
2. Passing port as URL parameter
3. Port detection if server is running
4. Fallback to file:// protocol if needed
"""

import argparse
import os
import socket
import sys
import webbrowser
from pathlib import Path

# Get script directory for relative paths
SCRIPT_DIR = Path(__file__).parent
MONITOR_HTML = SCRIPT_DIR / "claude_mpm_monitor.html"


def find_running_server():
    """Find any running Socket.IO server on common ports.

    WHY: If a server is already running, we want to connect to it
    automatically rather than requiring users to specify the port.

    Returns:
        int: Port number of running server, or None if not found
    """
    common_ports = [8080, 8081, 8082, 3000, 3001, 5000]

    for port in common_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(("127.0.0.1", port))
                if result == 0:
                    print(f"✓ Found Socket.IO server on port {port}")
                    return port
        except Exception:
            continue

    return None


def open_monitor(port: int = None):
    """Open the monitoring dashboard in browser.

    WHY: Users need easy access to the monitoring dashboard. This function
    handles URL construction and browser opening with the static HTML file.

    Args:
        port: Port number for the Socket.IO server (optional)
    """
    if not MONITOR_HTML.exists():
        print(f"❌ Monitor HTML file not found: {MONITOR_HTML}")
        print(
            "   Please ensure claude_mpm_monitor.html exists in the scripts directory"
        )
        sys.exit(1)

    # Construct URL with port parameter if provided
    file_url = f"file://{MONITOR_HTML.absolute()}"
    if port:
        file_url += f"?port={port}"

    try:
        print(f"🌐 Opening monitor: {file_url}")
        webbrowser.open(file_url)

        if port:
            print(f"📊 Monitor will connect to Socket.IO server on port {port}")
        else:
            print(f"📊 Monitor opened - you can specify server port in the UI")

    except Exception as e:
        print(f"⚠️  Failed to open browser automatically: {e}")
        print(f"📊 Please open manually: {file_url}")


def main():
    """Main entry point for the monitor launcher.

    WHY: This provides a simple interface for opening the monitoring dashboard
    with automatic server detection and port handling.
    """
    parser = argparse.ArgumentParser(
        description="Launch static HTML monitor for Claude MPM Socket.IO server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_monitor.py                    # Auto-detect server or open with UI
  python launch_monitor.py --port 8080       # Connect to specific port
  python launch_monitor.py --no-detect       # Skip auto-detection
        """,
    )

    parser.add_argument("--port", type=int, help="Socket.IO server port to connect to")
    parser.add_argument(
        "--no-detect", action="store_true", help="Skip automatic server detection"
    )

    args = parser.parse_args()

    print("📊 Claude MPM Monitor Launcher")
    print("=" * 35)

    port = args.port

    # Auto-detect running server if no port specified
    if not port and not args.no_detect:
        print("🔍 Looking for running Socket.IO server...")
        port = find_running_server()

        if not port:
            print("ℹ️  No running server detected - you can specify port in the UI")

    # Open the monitor
    open_monitor(port)

    print("\n✅ Monitor launched successfully")
    if port:
        print(f"   Connecting to: http://localhost:{port}")
    print(f"   HTML file: {MONITOR_HTML}")


if __name__ == "__main__":
    main()
