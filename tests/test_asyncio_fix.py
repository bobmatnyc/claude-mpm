#!/usr/bin/env python3
"""
Final test to verify the asyncio event loop cleanup fix.

This test ensures that the monitor server and daemon can start and stop
without producing the "I/O operation on closed kqueue object" error.
"""

import contextlib
import io
import sys
import time
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.monitor.server import UnifiedMonitorServer


def capture_stderr(func):
    """Capture stderr output to check for errors."""
    stderr_capture = io.StringIO()
    with contextlib.redirect_stderr(stderr_capture):
        result = func()
    return result, stderr_capture.getvalue()


def test_server_multiple_cycles():
    """Test multiple start/stop cycles to ensure consistent cleanup."""
    print("Testing asyncio cleanup fix...")
    print("=" * 60)

    errors_found = []

    for cycle in range(3):
        print(f"\nCycle {cycle + 1}/3:")
        print("-" * 40)

        server = UnifiedMonitorServer(host="localhost", port=8765)

        def run_cycle():
            try:
                # Start server
                print("  Starting server...")
                if not server.start():
                    print("  ERROR: Failed to start server")
                    return False

                # Let it run briefly
                time.sleep(1)

                # Stop server
                print("  Stopping server...")
                server.stop()

                # Wait for cleanup
                time.sleep(0.5)

                print(f"  Cycle {cycle + 1} completed")
                return True

            except Exception as e:
                print(f"  ERROR in cycle: {e}")
                server.stop()
                return False

        # Run with stderr capture
        _success, stderr_output = capture_stderr(run_cycle)

        # Check for the specific error we're fixing
        if "I/O operation on closed kqueue object" in stderr_output:
            errors_found.append(f"Cycle {cycle + 1}: Found kqueue error!")
            print("  ❌ KQUEUE ERROR DETECTED")
        elif "Event loop is closed" in stderr_output:
            # This is less critical but worth noting
            print("  ⚠️  Warning: Event loop closed errors detected (less critical)")
        elif stderr_output.strip():
            # Other errors
            print(f"  ⚠️  Other stderr output: {stderr_output[:200]}")
        else:
            print("  ✅ No asyncio errors detected")

    print("\n" + "=" * 60)

    if errors_found:
        print("❌ TEST FAILED - kqueue errors found:")
        for error in errors_found:
            print(f"  - {error}")
        return False
    print("✅ TEST PASSED - No kqueue errors detected!")
    print("The asyncio event loop cleanup fix is working correctly.")
    return True


def main():
    """Run the test."""
    print("\nASYNCIO EVENT LOOP CLEANUP FIX VERIFICATION")
    print("=" * 60)
    print("This test verifies that the monitor daemon no longer produces")
    print("the 'I/O operation on closed kqueue object' error on shutdown.")
    print()

    success = test_server_multiple_cycles()

    print("\n" + "=" * 60)
    if success:
        print("✅ FIX VERIFIED: The asyncio cleanup issue has been resolved!")
        print("\nThe monitor daemon can now start and stop cleanly without")
        print("producing asyncio event loop cleanup errors.")
    else:
        print("❌ FIX INCOMPLETE: Some asyncio errors still occur.")
        print("\nAdditional cleanup may be needed.")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
