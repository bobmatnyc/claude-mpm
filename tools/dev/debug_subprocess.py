#!/usr/bin/env python3
"""Debug subprocess orchestrator launch issues."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_mpm.core.claude_launcher import ClaudeLauncher


def main():
    print("🔍 Debugging Claude Launcher")
    print("=" * 80)

    # Create launcher
    launcher = ClaudeLauncher(model="opus", skip_permissions=True, log_level="DEBUG")

    # Simple test message
    test_message = "Say 'Hello World' and nothing else"

    print(f"Test message: {test_message}")
    print("\nLaunching Claude in print mode...\n")

    try:
        stdout, stderr, returncode = launcher.launch_oneshot(
            message=test_message, use_stdin=True, timeout=10
        )

        print(f"Return code: {returncode}")
        print(f"\nSTDOUT:\n{stdout}")
        print(f"\nSTDERR:\n{stderr}")

    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    main()
