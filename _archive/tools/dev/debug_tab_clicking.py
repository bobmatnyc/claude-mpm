#!/usr/bin/env python3
"""Debug tab clicking issues in the monitoring dashboard."""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def main():
    print("🔍 Debugging Tab Clicking Issues")
    print("=" * 60)

    # Open dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"

    print(f"\n📊 Opening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)

    # Suppress browser for tests
    os.environ["CLAUDE_MPM_NO_BROWSER"] = "1"

    print("\n📝 Generating test events...")

    # Generate various events to test all tabs
    test_scenarios = [
        "Read the file /Users/test/example.py",
        "Edit the file /Users/test/config.json and add a new setting",
        "Write a new file /Users/test/output.txt with some content",
        "Create a todo list with 3 items: fix bugs, add features, write tests",
        "Use the Grep tool to search for 'test' in the codebase",
        "Run ls -la to list files",
    ]

    for i, prompt in enumerate(test_scenarios, 1):
        print(f"\n{i}. {prompt}")

        cmd = [
            sys.executable,
            "-m",
            "claude_mpm",
            "run",
            "-i",
            prompt,
            "--non-interactive",
            "--monitor",
        ]

        subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        time.sleep(1)

    print("\n" + "=" * 60)
    print("🔍 Debugging Instructions:")
    print("\n1. Open Browser DevTools (F12)")
    print("   - Go to Console tab")
    print("   - Look for any JavaScript errors")

    print("\n2. Test Each Tab:")
    print("   a) Events Tab:")
    print("      - Click on any event")
    print("      - Module viewer should update")
    print("      - Check console for errors")

    print("\n   b) Agents Tab:")
    print("      - Click on any agent card")
    print("      - Should call showAgentDetails()")
    print("      - Module viewer should show event")

    print("\n   c) Tools Tab:")
    print("      - Click on any tool card")
    print("      - Should call showToolDetails()")
    print("      - Module viewer should show event")

    print("\n   d) Files Tab:")
    print("      - Click on any file operation")
    print("      - Should call showFileDetails()")
    print("      - Module viewer should show event")

    print("\n3. Check Console Logs:")
    print("   - Add this to console: `console.log(events)`")
    print("   - Verify events array has data")
    print("   - Check event indices match")

    print("\n4. Test Manual Click:")
    print("   - In console: `showFileDetails(0)`")
    print("   - Should update module viewer")
    print("   - If it works, onclick handler is the issue")

    print("\n5. Check Event Order:")
    print("   - Newest events should be at bottom")
    print("   - Auto-scroll should work")
    print("   - All tabs should have same order")


if __name__ == "__main__":
    main()
