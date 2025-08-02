#!/usr/bin/env python3
"""Open the dashboard statically in the browser."""

import os
import webbrowser
from pathlib import Path

def open_dashboard(port=8765, autoconnect=True):
    """Open the dashboard HTML file directly in the browser.
    
    Args:
        port: Socket.IO server port to connect to
        autoconnect: Whether to auto-connect on load
    """
    # Get the static index.html path (main entry point)
    dashboard_path = Path(__file__).parent / "templates" / "index.html"
    
    if not dashboard_path.exists():
        raise FileNotFoundError(f"Dashboard not found at {dashboard_path}")
    
    # Build URL with query parameters for Socket.IO connection
    dashboard_url = f"file://{dashboard_path.absolute()}?port={port}"
    if autoconnect:
        dashboard_url += "&autoconnect=true"
    
    print(f"🌐 Opening static dashboard: {dashboard_url}")
    print(f"📡 Dashboard will connect to Socket.IO server at localhost:{port}")
    webbrowser.open(dashboard_url)
    
    return dashboard_url

if __name__ == "__main__":
    # Test opening the dashboard
    open_dashboard()