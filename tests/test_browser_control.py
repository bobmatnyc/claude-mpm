#!/usr/bin/env python3
"""Demonstrate how to control browser opening for the monitor."""

import os
import subprocess
import sys
from pathlib import Path

def main():
    print("🌐 Browser Control for Monitor")
    print("=" * 50)
    
    print("\n1️⃣ Normal behavior (opens browser):")
    print("   claude-mpm run --monitor")
    print("   - This will open the browser automatically")
    
    print("\n2️⃣ Suppress browser opening (for tests/scripts):")
    print("   export CLAUDE_MPM_NO_BROWSER=1")
    print("   claude-mpm run --monitor")
    print("   - This will NOT open the browser")
    
    print("\n3️⃣ Testing with suppressed browser:")
    
    # Set environment variable to suppress browser
    os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
    
    cmd = [
        sys.executable, "-m", "claude_mpm", "run",
        "--monitor",
        "-i", "echo 'Testing without browser'",
        "--non-interactive"
    ]
    
    print(f"\n   Running: {' '.join(cmd)}")
    print("   With CLAUDE_MPM_NO_BROWSER=1")
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if "Browser opening suppressed" in result.stdout:
        print("\n   ✅ Browser was NOT opened (as expected)")
    else:
        print("\n   ❌ Browser opening was not suppressed")
    
    print("\n4️⃣ For your test scripts:")
    print("   Add this at the beginning:")
    print("   import os")
    print("   os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'")
    
    print("\n5️⃣ The dashboard URL will still be shown:")
    print("   You can manually open it when needed")
    print("   Or use it in automated tests")
    
    print("\n✨ This prevents multiple browser windows!")

if __name__ == "__main__":
    main()