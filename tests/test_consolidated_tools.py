#!/usr/bin/env python3
"""Test the consolidated tool tracking."""

import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🔧 Testing Consolidated Tool Tracking")
    print("=" * 50)
    
    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\nOpening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)
    
    print("\n📝 Generating tool operations...")
    
    # Test 1: File operations
    print("\n1️⃣ Testing file operations...")
    cmd = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", "Read scripts/test_consolidated_tools.py and count the lines",
        "--non-interactive", "--monitor"
    ]
    subprocess.run(cmd, cwd=Path(__file__).parent.parent, capture_output=True, timeout=30)
    
    time.sleep(2)
    
    # Test 2: Multiple tools
    print("\n2️⃣ Testing multiple tools...")
    cmd = [
        sys.executable, "-m", "claude_mpm", "run", 
        "-i", 'List files in scripts/ directory that contain "test"',
        "--non-interactive", "--monitor"
    ]
    subprocess.run(cmd, cwd=Path(__file__).parent.parent, capture_output=True, timeout=30)
    
    print("\n" + "=" * 50)
    print("🔧 CONSOLIDATED TOOL VIEW")
    print("=" * 50)
    
    print("\n✅ What's New in Tools Tab:")
    print("- Single entry per tool operation (no separate start/finish)")
    print("- Shows operation target (file, command, pattern, etc.)")
    print("- Displays duration (e.g., 1.2s, 250ms)")
    print("- Status icons: ✅ success, ❌ failed, ⏳ in progress")
    
    print("\n📊 Tool Target Examples:")
    print("- Read: shows file path")
    print("- Grep: shows pattern and search path") 
    print("- Bash: shows command")
    print("- Task: shows agent type")
    print("- LS: shows directory path")
    
    print("\n🎯 Check the Tools Tab:")
    print("1. Click on the 🔧 Tools tab")
    print("2. See consolidated operations with:")
    print("   - Start time and duration")
    print("   - Target of the operation")
    print("   - Which agent used the tool")
    print("   - Success/failure status")
    
    print("\n✨ Tools are now tracked with full operation details!")

if __name__ == "__main__":
    main()