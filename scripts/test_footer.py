#!/usr/bin/env python3
"""Test the new footer display."""

import os
import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🦶 Testing Dashboard Footer")
    print("=" * 50)
    
    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\nOpening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)
    
    print("\n📝 Generating a test event to trigger session...")
    
    # Don't open another browser window
    os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
    
    cmd = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", "echo 'Testing footer display'",
        "--non-interactive",
        "--monitor"
    ]
    
    print(f"\nRunning from: {os.getcwd()}")
    print(f"Command: {' '.join(cmd)}")
    
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
    print("🦶 FOOTER INFORMATION")
    print("=" * 50)
    
    print("\n✨ What's New:")
    print("- Fixed footer at bottom of dashboard")
    print("- Shows session ID (abbreviated)")
    print("- Shows working directory (shortened)")
    print("- Shows current git branch")
    
    print("\n📊 Footer Components:")
    print("1. **Session ID**: First 8 chars of session UUID")
    print("   - Hover to see full ID")
    print("2. **Directory**: Last 2 parts of path")
    print("   - Hover to see full path")
    print("3. **Branch**: Current git branch name")
    print("   - Shows 'not a git repo' if not in git")
    
    print("\n🎨 Design:")
    print("- Dark semi-transparent background")
    print("- Centered content with dividers")
    print("- Monospace font for values")
    print("- Subtle styling that doesn't distract")
    
    print("\n💡 Tips:")
    print("- Footer updates when new session starts")
    print("- Information persists across tab switches")
    print("- Useful for tracking which project/branch you're monitoring")

if __name__ == "__main__":
    main()