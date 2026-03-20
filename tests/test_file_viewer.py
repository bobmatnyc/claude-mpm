#!/usr/bin/env python3
"""
Test script for verifying file viewer functionality in the dashboard.

This script:
1. Starts the dashboard server
2. Opens the dashboard
3. Tests file viewer operations
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))


def main():
    """Main test function."""
    print("=" * 60)
    print("FILE VIEWER TEST SCRIPT")
    print("=" * 60)

    print("\n📋 Test Plan:")
    print("1. Dashboard will open")
    print("2. Click on any file in the Files tab")
    print("3. Check if file viewer modal opens")
    print("4. Test the close button")
    print("5. Check modal width")

    print("\n🚀 Starting dashboard...")

    # Run the dashboard
    try:
        subprocess.run(
            [sys.executable, "-m", "claude_mpm.cli.commands.monitor"], check=False
        )
    except KeyboardInterrupt:
        print("\n\n✅ Test complete. Check the console for any errors.")
        print("\nExpected behavior:")
        print("- Files should load when clicked")
        print("- Close button (×) should close the modal")
        print("- Modal should be ~95% of viewport width")
        print("- Console logs should show file loading progress")

        print("\n📝 Summary of fixes applied:")
        print("1. Added comprehensive logging to track file loading")
        print("2. Fixed close button functionality")
        print("3. CSS already sets modal width to 95vw")
        print("4. Improved error handling and display")
        print("5. Consolidated file viewer implementations")


if __name__ == "__main__":
    main()
