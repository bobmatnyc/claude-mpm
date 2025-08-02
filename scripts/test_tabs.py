#!/usr/bin/env python3
"""Test the new tabbed interface."""

import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🔬 Testing Tabbed Interface")
    print("=" * 50)
    
    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\nOpening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)
    
    print("\n📝 Generating test events with file operations...")
    
    # Generate a test that uses files
    cmd = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", "Read the file scripts/test_tabs.py and tell me what it does",
        "--non-interactive",
        "--monitor"
    ]
    
    print("Running command to generate events...")
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0:
        print("✅ Command completed successfully")
    else:
        print(f"❌ Error: {result.stderr[:100]}")
    
    print("\n" + "=" * 50)
    print("📊 TABBED INTERFACE GUIDE")
    print("=" * 50)
    
    print("\n🔖 Available Tabs:")
    print("1. 📊 Events - All events (current view)")
    print("2. 🤖 Agents - Agent delegations via Task tool")
    print("3. 🔧 Tools - All tool usage with agent info")
    print("4. 📁 Files - File operations (Read/Write/Edit)")
    
    print("\n📝 What to Check:")
    print("- Click each tab to see filtered content")
    print("- Events tab shows all events as before")
    print("- Agents tab shows only Task tool calls to agents")
    print("- Tools tab shows all tool usage")
    print("- Files tab shows file operations")
    
    print("\n🎯 Test Results:")
    print("- You should see the Read operation in Files tab")
    print("- Tools tab should show the Read tool usage")
    print("- Events tab contains all events")
    
    print("\n✨ The tabbed interface is now active!")

if __name__ == "__main__":
    main()