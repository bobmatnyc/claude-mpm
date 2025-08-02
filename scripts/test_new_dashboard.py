#!/usr/bin/env python3
"""Test the new modular dashboard setup."""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.web.open_dashboard import open_dashboard

def main():
    print("🧪 Testing New Modular Dashboard")
    print("=" * 60)
    
    print("\n1. Opening dashboard with static file serving...")
    dashboard_url = open_dashboard(port=8765, autoconnect=True)
    
    print(f"\n✅ Dashboard opened: {dashboard_url}")
    
    print("\n2. Starting Socket.IO server...")
    # Start the Socket.IO server
    server_process = subprocess.Popen(
        [sys.executable, "scripts/start_persistent_socketio_server.py"],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    time.sleep(3)
    print("✅ Socket.IO server should be running")
    
    print("\n3. Generate a test event...")
    os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
    
    cmd = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", "echo 'Testing new modular dashboard'",
        "--non-interactive",
        "--monitor"
    ]
    
    subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    print("\n✅ Test event sent")
    
    print("\n4. Verification steps:")
    print("   - Check if dashboard loads correctly")
    print("   - Verify CSS styles are applied") 
    print("   - Check if JavaScript modules load")
    print("   - Confirm Socket.IO connection works")
    print("   - See if events appear in the dashboard")
    
    print("\n📂 New structure:")
    print("   src/claude_mpm/web/")
    print("     ├── templates/dashboard.html")
    print("     ├── static/css/dashboard.css")
    print("     └── static/js/")
    print("         ├── dashboard.js")
    print("         ├── socket-client.js")
    print("         └── components/")
    
    print("\n🎉 Dashboard is now modular and served statically!")
    print("\nPress Ctrl+C to stop the server...")
    
    try:
        server_process.wait()
    except KeyboardInterrupt:
        server_process.terminate()
        print("\n✅ Server stopped")

if __name__ == "__main__":
    main()