#!/usr/bin/env python3
"""Test the JSON viewer in event analysis."""

import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("📋 Testing JSON Event Viewer")
    print("=" * 50)
    
    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\nOpening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)
    
    print("\n📝 Generating test event...")
    
    # Generate an event with rich data
    cmd = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", "echo 'Testing JSON viewer'",
        "--non-interactive",
        "--monitor"
    ]
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0:
        print("✅ Event generated successfully")
    else:
        print(f"❌ Error: {result.stderr[:100]}")
    
    print("\n" + "=" * 50)
    print("📋 JSON VIEWER FEATURES")
    print("=" * 50)
    
    print("\n✨ What's New:")
    print("- Full JSON object display below event summary")
    print("- Syntax highlighting for better readability")
    print("- Scrollable view for large objects")
    print("- Preserves all event data for inspection")
    
    print("\n🎨 Syntax Highlighting:")
    print("- Keys: Blue (#0969da)")
    print("- String values: Dark blue (#0a3069)")
    print("- Numbers: Blue (#0550ae)")
    print("- Booleans: Red (#cf222e)")
    print("- Null: Gray (#6e7781)")
    
    print("\n📝 How to Use:")
    print("1. Click on any event in the Events tab")
    print("2. Look at the Event Analysis panel (left side)")
    print("3. See the event summary cards at the top")
    print("4. Scroll down to see 📋 Full Event JSON section")
    print("5. Inspect the complete event structure")
    
    print("\n🔍 What You Can Inspect:")
    print("- Event type and timestamp")
    print("- Session IDs and agent information")
    print("- Tool parameters and results")
    print("- Error messages and stack traces")
    print("- Any custom data in the event")
    
    print("\n💡 Tip: Use arrow keys to quickly navigate events!")

if __name__ == "__main__":
    main()