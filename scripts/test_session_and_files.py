#!/usr/bin/env python3
"""Test the updated session selector and file path display."""

import os
import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🧪 Testing Session Selector and File Paths")
    print("=" * 60)
    
    # Suppress automatic browser opening
    os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
    
    # Open the dashboard manually first
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\n📊 Opening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)
    
    print("\n🔄 Generating test sessions with different working directories...")
    
    # Test 1: Session from project root
    print("\n1️⃣ Session from project root:")
    cmd1 = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", "Read the README.md file",
        "--non-interactive",
        "--monitor"
    ]
    
    print(f"   Working dir: {Path.cwd()}")
    result1 = subprocess.run(
        cmd1,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        timeout=30
    )
    time.sleep(1)
    
    # Test 2: Session from scripts directory
    print("\n2️⃣ Session from scripts directory:")
    cmd2 = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", "List files in current directory",
        "--non-interactive",
        "--monitor"
    ]
    
    scripts_dir = Path(__file__).parent
    print(f"   Working dir: {scripts_dir}")
    result2 = subprocess.run(
        cmd2,
        cwd=scripts_dir,
        capture_output=True,
        text=True,
        timeout=30
    )
    time.sleep(1)
    
    # Test 3: File operations with various paths
    print("\n3️⃣ Testing file operations with different paths:")
    file_ops = [
        "Read the file /Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/run.py",
        "Check if ./scripts/test_example.py exists",
        "Look at ../docs/MONITORING_ROADMAP.md",
        "Read ~/.bashrc if it exists"
    ]
    
    for op in file_ops:
        print(f"\n   Testing: {op}")
        cmd = [
            sys.executable, "-m", "claude_mpm", "run",
            "-i", op,
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
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("✅ Test sessions generated!")
    print("\n🔍 Check the dashboard for:")
    print("1. **Session Selector** (Row 2 of header):")
    print("   - Should show dropdown with format: 'SessionID | path | time'")
    print("   - Hover over options to see full details")
    print("   - Active sessions marked with ●")
    print("\n2. **Files Tab**:")
    print("   - Click on 'Files' tab")
    print("   - Should show full file paths next to operations")
    print("   - Long paths abbreviated with '.../'")
    print("   - Hover to see full path")
    print("\n3. **Session Switching**:")
    print("   - Select different sessions from dropdown")
    print("   - Events should filter by selected session")
    print("   - 'All Sessions' shows everything")
    
    print("\n💡 Tips:")
    print("- The session selector shows working directory for each session")
    print("- File paths are monospace font for clarity")
    print("- Agent name shown in parentheses after file path")

if __name__ == "__main__":
    main()