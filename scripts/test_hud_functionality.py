#!/usr/bin/env python3
"""
Test HUD functionality in the dashboard.

This script launches the Socket.IO server and opens the dashboard
to manually test the HUD toggle functionality.
"""

import sys
import time
import webbrowser
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.websocket_server import SocketIOServer

def main():
    """Launch server and open dashboard for HUD testing."""
    
    print("🚀 Starting Socket.IO server for HUD testing...")
    
    # Start server
    server = SocketIOServer(port=8765)
    server.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Open dashboard in browser
    dashboard_url = "http://localhost:8765"
    print(f"📊 Opening dashboard at {dashboard_url}")
    print("\n" + "="*60)
    print("HUD Testing Instructions:")
    print("="*60)
    print("1. The dashboard should open in your browser")
    print("2. Initially, the HUD button should be DISABLED")
    print("3. Connect to the Socket.IO server if not auto-connected")
    print("4. Select a session from the dropdown (or use 'All Sessions')")
    print("5. The HUD button should become ENABLED")
    print("6. Click the HUD button to toggle HUD mode")
    print("7. In HUD mode, you should see a Cytoscape.js visualization")
    print("8. Click 'Normal View' to return to normal mode")
    print("9. Test that switching sessions disables/enables HUD appropriately")
    print("="*60)
    print("\nPress Ctrl+C to stop the server...")
    
    try:
        webbrowser.open(dashboard_url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print(f"Please manually open: {dashboard_url}")
    
    try:
        # Keep server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping server...")
        server.stop()
        print("✅ Server stopped")

if __name__ == "__main__":
    main()