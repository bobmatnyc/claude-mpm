#!/usr/bin/env python3
"""
Test script to verify code tree functionality in the Claude MPM dashboard.

This script will:
1. Start the dashboard
2. Wait for user to test the code tree
3. Provide instructions on what to look for in console logs
"""

import subprocess
import sys
import time
import webbrowser


def main():
    print("=" * 60)
    print("CODE TREE DEBUGGING TEST")
    print("=" * 60)
    print()
    print("This test will help debug the code tree visualization.")
    print()
    print("Starting the Claude MPM dashboard...")
    print()

    # Start the dashboard
    try:
        # Use the same command that would normally start the dashboard
        subprocess.Popen([sys.executable, "-m", "claude_mpm", "dashboard"])

        # Give it time to start
        time.sleep(3)

        # Open browser
        webbrowser.open("http://localhost:5000")

        print("Dashboard started! Opening browser...")
        print()
        print("TESTING INSTRUCTIONS:")
        print("-" * 40)
        print("1. Open the browser's Developer Console (F12)")
        print("2. Click on the 'Code' tab in the dashboard")
        print("3. Wait for auto-discovery to complete")
        print("4. Look for these console messages:")
        print()
        print("   📤 Sending top-level discovery request")
        print("   📦 Received top-level discovery")
        print("   🔎 Looking for root node")
        print("   🌳 Populating root node with children")
        print()
        print("5. Try clicking on 'src' directory")
        print("6. Look for these console messages:")
        print()
        print("   🔍 Node clicked")
        print("   🔗 ensureFullPath called")
        print("   📤 Sending discovery request")
        print("   📥 Received directory discovery")
        print()
        print("7. Check if the tree shows:")
        print("   - Root node with proper name")
        print("   - Children nodes (src, tests, docs, etc.)")
        print("   - Ability to expand directories")
        print()
        print("EXPECTED BEHAVIOR:")
        print("-" * 40)
        print("✓ Root node should auto-populate with top-level items")
        print("✓ Clicking 'src' should expand to show its contents")
        print("✓ All paths should be properly logged in console")
        print()
        print("TROUBLESHOOTING:")
        print("-" * 40)
        print("If 'src' doesn't expand, check console for:")
        print("- 'Node with path \"src\" not found'")
        print("- List of all available paths")
        print("- Any error messages")
        print()
        print("Press Ctrl+C to stop the dashboard when done testing...")

        # Keep running until interrupted
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nStopping dashboard...")
        print("Test complete!")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
