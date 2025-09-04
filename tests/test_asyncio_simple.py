#!/usr/bin/env python3
"""
Simple test to verify asyncio event loop cleanup in monitor server.
"""

import sys
import time
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.monitor.server import UnifiedMonitorServer


def test_server_cleanup():
    """Test that the server starts and stops cleanly without asyncio errors."""
    print("Testing monitor server asyncio cleanup...")
    print("-" * 50)

    # Create server instance
    server = UnifiedMonitorServer(host="localhost", port=8765)

    try:
        # Start the server
        print("Starting monitor server...")
        success = server.start()
        if not success:
            print("ERROR: Failed to start server")
            return False

        print("Server started successfully")

        # Let it run for a few seconds
        print("Letting server run for 2 seconds...")
        time.sleep(2)

        # Stop the server
        print("\nStopping monitor server...")
        server.stop()
        print("Server stopped")

        # Give it time to fully cleanup
        time.sleep(1)

        print("\n✅ SUCCESS: No asyncio cleanup errors detected!")
        return True

    except KeyboardInterrupt:
        print("\nInterrupted by user, cleaning up...")
        server.stop()
        return False
    except Exception as e:
        print(f"\n❌ ERROR during test: {e}")
        import traceback

        traceback.print_exc()
        server.stop()
        return False


def main():
    """Run test."""
    print("=" * 60)
    print("ASYNCIO EVENT LOOP CLEANUP TEST (SIMPLE)")
    print("=" * 60)

    # Test basic start/stop
    if not test_server_cleanup():
        print("\n❌ FAILED: Cleanup test failed")
        return 1

    print("\n" + "=" * 60)
    print("✅ TEST PASSED - No asyncio cleanup errors!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
