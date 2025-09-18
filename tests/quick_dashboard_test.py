#!/usr/bin/env python3
"""Quick test to verify activity dashboard works."""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def main():
    print("🚀 Starting Claude MPM Monitor Server...")
    print("=" * 60)

    # Start the server using the CLI
    server_process = subprocess.Popen(
        ["python", "-m", "claude_mpm.cli.main", "monitor", "--port", "5001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    print("⏳ Waiting for server to start...")
    time.sleep(3)

    # Check if server is running
    try:
        import requests

        response = requests.get("http://localhost:5001/api/status", timeout=2)
        if response.status_code == 200:
            print("✅ Server is running!")
            print(f"   Status: {response.json()}")
        else:
            print("❌ Server returned unexpected status:", response.status_code)
    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        server_process.terminate()
        return

    print("\n📊 Available Dashboards:")
    print("=" * 60)
    print("🎯 Activity Dashboard: http://localhost:5001/static/activity.html")
    print("📡 Events Monitor:     http://localhost:5001/static/events.html")
    print("🤖 Agents Monitor:     http://localhost:5001/static/agents.html")
    print("🔧 Tools Monitor:      http://localhost:5001/static/tools.html")
    print("📁 Files Monitor:      http://localhost:5001/static/files.html")
    print("=" * 60)

    # Open the activity dashboard in browser
    dashboard_url = "http://localhost:5001/static/activity.html"
    print(f"\n🌐 Opening {dashboard_url} in your browser...")
    webbrowser.open(dashboard_url)

    print("\n✨ Dashboard is ready!")
    print("Press Ctrl+C to stop the server...")

    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        server_process.terminate()
        print("👋 Goodbye!")


if __name__ == "__main__":
    main()
