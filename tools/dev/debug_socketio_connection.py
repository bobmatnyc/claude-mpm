#!/usr/bin/env python3
"""Debug Socket.IO connection issues in the dashboard."""

import os
import subprocess
import sys
import time
from pathlib import Path


def check_socketio_server():
    """Check if Socket.IO server is running."""
    print("🔍 Debugging Socket.IO Connection Issues")
    print("=" * 60)

    print("\n1. Checking if Socket.IO server is running...")

    # Check if the server process is running
    result = subprocess.run(["ps", "aux"], capture_output=True, text=True)

    if "socketio_server" in result.stdout:
        print("✅ Socket.IO server process found")
    else:
        print("❌ Socket.IO server process not found")
        print("   Try running: python scripts/start_persistent_socketio_server.py")

    # Check if port 8765 is in use
    print("\n2. Checking port 8765...")
    result = subprocess.run(["lsof", "-i", ":8765"], capture_output=True, text=True)

    if result.stdout:
        print("✅ Port 8765 is in use")
        print(f"   {result.stdout.split()[0]}")
    else:
        print("❌ Port 8765 is not in use")
        print("   The Socket.IO server may not be running")

    print("\n3. Testing Socket.IO connection...")

    # Try a simple connection test
    test_script = """
import socketio
import sys

sio = socketio.Client()

@sio.event
def connect():
    print("✅ Successfully connected to Socket.IO server")
    sio.disconnect()
    sys.exit(0)

@sio.event
def connect_error(data):
    print(f"❌ Connection error: {data}")
    sys.exit(1)

try:
    sio.connect('http://localhost:8765', wait_timeout=5)
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    sys.exit(1)
"""

    with open("/tmp/test_socketio.py", "w") as f:
        f.write(test_script)

    result = subprocess.run(
        [sys.executable, "/tmp/test_socketio.py"], capture_output=True, text=True
    )

    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}")


def check_dashboard_issues():
    """Check for common dashboard issues."""
    print("\n4. Checking dashboard file...")

    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"

    if not dashboard_path.exists():
        print("❌ Dashboard file not found!")
        return

    with open(dashboard_path, "r") as f:
        content = f.read()

    # Check for Socket.IO library
    if '<script src="https://cdn.socket.io' in content:
        print("✅ Socket.IO client library included")
    else:
        print("❌ Socket.IO client library not found")

    # Check connection code
    if "io(" in content and "connectSocket" in content:
        print("✅ Connection code found")
    else:
        print("❌ Connection code may be missing")

    # Check for syntax errors in recent changes
    print("\n5. Common issues to check:")
    print("   - JavaScript syntax errors (check browser console)")
    print("   - Port mismatch (dashboard using different port)")
    print("   - CORS issues (check server configuration)")
    print("   - Socket.IO version mismatch")


def suggest_fixes():
    """Suggest fixes for common issues."""
    print("\n🔧 Troubleshooting Steps:")
    print("=" * 60)

    print("\n1. Start Socket.IO server if not running:")
    print("   python scripts/start_persistent_socketio_server.py")

    print("\n2. Check browser console for errors:")
    print("   - Open dashboard in browser")
    print("   - Press F12 to open DevTools")
    print("   - Check Console tab for JavaScript errors")

    print("\n3. Verify connection in dashboard:")
    print("   - Look for 'Connecting...' status")
    print("   - Check if it changes to 'Connected'")
    print("   - Try clicking 'Connect' button manually")

    print("\n4. Test with simple event:")
    print("   claude-mpm run -i 'echo test' --monitor")

    print("\n5. Check URL parameters:")
    print(
        "   - Open: file:///.../claude_mpm_socketio_dashboard.html?autoconnect=true&port=8765"
    )
    print("   - Ensure port matches server port")


def main():
    """Run diagnostics."""
    check_socketio_server()
    check_dashboard_issues()
    suggest_fixes()

    print("\n📋 Next Steps:")
    print("1. Check browser console for specific error messages")
    print("2. Verify the connectSocket() function is being called")
    print("3. Look for any recent changes that might have broken the connection")


if __name__ == "__main__":
    main()
