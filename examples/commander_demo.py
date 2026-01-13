#!/usr/bin/env python3
"""Demo script for TmuxOrchestrator.

This demonstrates the basic usage of the TmuxOrchestrator class for
managing tmux sessions and panes.

Usage:
    python examples/commander_demo.py

Requirements:
    - tmux must be installed
"""

import sys
import time
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.commander import TmuxNotFoundError, TmuxOrchestrator


def main():
    """Run TmuxOrchestrator demo."""
    try:
        # Create orchestrator
        print("Creating TmuxOrchestrator...")
        orchestrator = TmuxOrchestrator(session_name="demo-commander")

        # Create session
        print("Creating tmux session 'demo-commander'...")
        created = orchestrator.create_session()
        if created:
            print("✓ Session created")
        else:
            print("✓ Session already exists")

        # Create first pane
        print("\nCreating pane for project 1...")
        target1 = orchestrator.create_pane("proj1", "/tmp")  # nosec B108
        print(f"✓ Created pane with target: {target1}")

        # Send commands to first pane
        print("\nSending commands to pane 1...")
        orchestrator.send_keys(target1, "echo 'Hello from pane 1'")
        orchestrator.send_keys(target1, "pwd")
        time.sleep(0.5)  # Give commands time to execute

        # Capture output
        print("\nCapturing output from pane 1...")
        output = orchestrator.capture_output(target1, lines=10)
        print("Output:")
        print(output)

        # Create second pane
        print("\nCreating pane for project 2...")
        target2 = orchestrator.create_pane("proj2", "/var")
        print(f"✓ Created pane with target: {target2}")

        # Send commands to second pane
        orchestrator.send_keys(target2, "echo 'Hello from pane 2'")
        orchestrator.send_keys(target2, "pwd")
        time.sleep(0.5)

        # List all panes
        print("\nListing all panes...")
        panes = orchestrator.list_panes()
        for pane in panes:
            print(
                f"  {pane['id']}: {pane['path']} (PID: {pane['pid']}, Active: {pane['active']})"
            )

        # Cleanup
        print("\nCleaning up...")
        print("Killing pane 1...")
        orchestrator.kill_pane(target1)
        print("✓ Pane 1 killed")

        print("\nKilling entire session...")
        orchestrator.kill_session()
        print("✓ Session killed")

        print("\n✅ Demo completed successfully!")

    except TmuxNotFoundError:
        print("❌ Error: tmux is not installed or not found in PATH")
        print("Please install tmux to use this demo:")
        print("  macOS: brew install tmux")
        print("  Ubuntu/Debian: sudo apt-get install tmux")
        print("  Fedora/RHEL: sudo dnf install tmux")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
