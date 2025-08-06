#!/usr/bin/env python3
"""Test script to verify the compact dashboard design."""

import subprocess
import time
import webbrowser
from pathlib import Path

def main():
    print("🚀 Testing compact dashboard design...")
    
    # Start the Socket.IO server
    print("Starting Socket.IO server...")
    server_process = subprocess.Popen(
        ["python", "-m", "claude_mpm", "--monitor"],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give server time to start
    time.sleep(2)
    
    # Open dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"Opening dashboard at: {dashboard_url}")
    webbrowser.open(dashboard_url)
    
    print("\n✅ Dashboard opened!")
    print("Check the following:")
    print("1. Compact header with title and connection status on the same line")
    print("2. Event counters in small widgets in the header")
    print("3. Session selection dropdown in the second row")
    print("4. Connection info (Socket ID, Server status, Port) in the second row")
    print("\nPress Ctrl+C to stop the server...")
    
    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\n\nStopping server...")
        server_process.terminate()
        server_process.wait()
        print("Server stopped.")

if __name__ == "__main__":
    main()