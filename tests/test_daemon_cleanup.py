#!/usr/bin/env python3
"""
Test that the monitor daemon starts and stops cleanly.
"""

import sys
import time
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.monitor.daemon import UnifiedMonitorDaemon


def test_daemon():
    """Test daemon start/stop."""
    print("Testing monitor daemon cleanup...")
    print("-" * 50)

    daemon = UnifiedMonitorDaemon(
        host="localhost",
        port=8765,
        daemon_mode=False,  # Foreground for testing
    )

    try:
        print("Starting daemon...")
        if not daemon.start():
            print("ERROR: Failed to start daemon")
            return False

        print("Daemon started successfully")
        time.sleep(2)

        print("Stopping daemon...")
        daemon.stop()
        print("Daemon stopped")

        time.sleep(1)
        print("✅ SUCCESS: No errors detected!")
        return True

    except KeyboardInterrupt:
        print("\nInterrupted, cleaning up...")
        daemon.stop()
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        daemon.stop()
        return False


if __name__ == "__main__":
    success = test_daemon()
    sys.exit(0 if success else 1)
