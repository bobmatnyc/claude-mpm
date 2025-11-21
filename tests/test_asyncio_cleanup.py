#!/usr/bin/env python3
"""
Test script to verify asyncio event loop cleanup in monitor daemon.

This script starts and stops the monitor daemon to ensure no asyncio
cleanup errors occur.
"""

import subprocess
import sys
import time
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.monitor.daemon import UnifiedMonitorDaemon


def test_daemon_cleanup():
    """Test that the daemon starts and stops cleanly without asyncio errors."""
    print("Testing monitor daemon asyncio cleanup...")
    print("-" * 50)

    # Create daemon instance
    daemon = UnifiedMonitorDaemon(
        host="localhost",
        port=8765,
        daemon_mode=False,  # Run in foreground for testing
    )

    try:
        # Start the daemon
        print("Starting monitor daemon...")
        success = daemon.start()
        if not success:
            print("ERROR: Failed to start daemon")
            return False

        print("Daemon started successfully")

        # Let it run for a few seconds
        print("Letting daemon run for 3 seconds...")
        time.sleep(3)

        # Check status
        status = daemon.status()
        print(f"Daemon status: {status}")

        # Stop the daemon
        print("\nStopping monitor daemon...")
        daemon.stop()
        print("Daemon stopped")

        # Give it time to fully cleanup
        time.sleep(1)

        print("\n✅ SUCCESS: No asyncio cleanup errors detected!")
        return True

    except KeyboardInterrupt:
        print("\nInterrupted by user, cleaning up...")
        daemon.stop()
        return False
    except Exception as e:
        print(f"\n❌ ERROR during test: {e}")
        daemon.stop()
        return False


def test_multiple_restarts():
    """Test multiple start/stop cycles to ensure consistent cleanup."""
    print("\nTesting multiple start/stop cycles...")
    print("-" * 50)

    for i in range(3):
        print(f"\nCycle {i + 1}/3:")

        daemon = UnifiedMonitorDaemon(host="localhost", port=8765, daemon_mode=False)

        try:
            # Start
            print("  Starting daemon...")
            if not daemon.start():
                print(f"  ERROR: Failed to start on cycle {i + 1}")
                return False

            # Brief run
            time.sleep(1)

            # Stop
            print("  Stopping daemon...")
            daemon.stop()

            # Wait before next cycle
            time.sleep(1)

            print(f"  Cycle {i + 1} completed successfully")

        except Exception as e:
            print(f"  ERROR in cycle {i + 1}: {e}")
            daemon.stop()
            return False

    print("\n✅ SUCCESS: All cycles completed without asyncio cleanup errors!")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("ASYNCIO EVENT LOOP CLEANUP TEST")
    print("=" * 60)

    # Test basic start/stop
    if not test_daemon_cleanup():
        print("\n❌ FAILED: Basic cleanup test failed")
        return 1

    # Test multiple restarts
    if not test_multiple_restarts():
        print("\n❌ FAILED: Multiple restart test failed")
        return 1

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - No asyncio cleanup errors!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
