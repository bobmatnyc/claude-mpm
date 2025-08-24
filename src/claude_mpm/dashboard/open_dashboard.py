#!/usr/bin/env python3
"""Open the dashboard statically in the browser."""

import webbrowser
from pathlib import Path

try:
    from ..services.port_manager import PortManager
except ImportError:
    # Fallback for when running as standalone script
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from claude_mpm.services.port_manager import PortManager


def discover_socketio_port():
    """Discover the port of the running SocketIO server, preferring 8765."""
    try:
        port_manager = PortManager()
        instances = port_manager.list_active_instances()

        if instances:
            # First, check if port 8765 is being used
            for instance in instances:
                if instance.get("port") == 8765:
                    return 8765

            # If 8765 is not available, return the first active instance port
            return instances[0].get("port", 8765)
        print("⚠️  No active SocketIO instances found, using default port 8765")
        return 8765
    except Exception as e:
        print(f"⚠️  Failed to discover SocketIO port: {e}")
        print("   Using default port 8765")
        return 8765


def open_dashboard(port=8765, autoconnect=True):
    """Open the dashboard HTML file directly in the browser.

    Args:
        port: Socket.IO server port to connect to (defaults to 8765, auto-discovers if needed)
        autoconnect: Whether to auto-connect on load
    """
    # If default port 8765 is specified, check if we need to auto-discover
    if port == 8765:
        discovered_port = discover_socketio_port()
        if discovered_port != 8765:
            print(
                f"🔍 SocketIO server found on port {discovered_port} instead of default 8765"
            )
            port = discovered_port
    # Build HTTP URL to connect to the SocketIO server's dashboard
    dashboard_url = f"http://localhost:{port}"

    print(f"🌐 Opening dashboard: {dashboard_url}")
    print(f"📡 Dashboard served by Socket.IO server at localhost:{port}")
    webbrowser.open(dashboard_url)

    return dashboard_url


if __name__ == "__main__":
    # Test opening the dashboard
    open_dashboard()
