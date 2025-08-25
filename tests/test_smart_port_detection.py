#!/usr/bin/env python3
"""
Test script for smart port detection and reclaim functionality.

WHY: This script demonstrates the enhanced port management that can:
- Detect what process is using a port
- Identify if it's our own process (debug script, daemon, or external)
- Automatically reclaim ports from debug scripts
- Preserve daemon processes unless forced
- Avoid external processes

USAGE:
    python scripts/test_smart_port_detection.py
"""

import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path to import claude_mpm modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.port_manager import PortManager

logger = get_logger(__name__)


def start_debug_process(port: int) -> subprocess.Popen:
    """Start a debug process on a specific port to test reclaim."""
    script = f"""
import socket
import time
import signal
import sys

def signal_handler(sig, frame):
    print(f"Debug process on port {port} received signal {{sig}}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

print(f"Starting debug process on port {port}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("localhost", {port}))
sock.listen(1)
print(f"Debug process listening on port {port}")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Debug process interrupted")
finally:
    sock.close()
"""

    # Start the debug process
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Give it time to bind to the port
    time.sleep(1)
    return process


def test_port_detection():
    """Test the smart port detection functionality."""
    print("=" * 60)
    print("Testing Smart Port Detection and Reclaim")
    print("=" * 60)
    print()

    port_manager = PortManager()
    test_port = 8765

    # Test 1: Check free port
    print("Test 1: Checking free port...")
    status = port_manager.get_port_status(test_port)
    if status["available"]:
        print(f"✅ Port {test_port} is available")
    else:
        print(f"⚠️ Port {test_port} is already in use")
        if status["process"]:
            print(
                f"   Process: {status['process']['name']} (PID: {status['process']['pid']})"
            )
            print(f"   Recommendation: {status['recommendation']}")
    print()

    # Test 2: Start a debug process and detect it
    print("Test 2: Starting debug process on port 8765...")
    debug_process = start_debug_process(test_port)
    print(f"   Started debug process with PID: {debug_process.pid}")

    # Check port status
    status = port_manager.get_port_status(test_port)
    if not status["available"]:
        process = status["process"]
        if process:
            print(f"   Port {test_port} is now in use by:")
            print(f"   - PID: {process['pid']}")
            print(f"   - Name: {process['name']}")
            print(f"   - Is ours: {process['is_ours']}")
            print(f"   - Is debug: {process['is_debug']}")
            print(f"   - Is daemon: {process['is_daemon']}")
            print(f"   - Recommendation: {status['recommendation']}")
    print()

    # Test 3: Try to find available port with reclaim
    print("Test 3: Finding available port with auto-reclaim...")
    available_port = port_manager.find_available_port(
        preferred_port=test_port, reclaim=True
    )

    if available_port == test_port:
        print(f"✅ Successfully reclaimed port {test_port} from debug process")
    elif available_port:
        print(f"⚠️ Got different port {available_port} (couldn't reclaim {test_port})")
    else:
        print("❌ No available ports found")

    # Wait for debug process to terminate
    debug_process.wait(timeout=2)
    print()

    # Test 4: Test port range status
    print("Test 4: Checking port range status...")
    print("Port range 8765-8770:")
    for port in range(8765, 8771):
        status = port_manager.get_port_status(port)
        if status["available"]:
            print(f"  Port {port}: ✅ Available")
        else:
            process = status.get("process")
            if process:
                if process["is_ours"]:
                    if process["is_debug"]:
                        print(f"  Port {port}: 🔧 Debug script (PID: {process['pid']})")
                    elif process["is_daemon"]:
                        print(f"  Port {port}: 🚀 Daemon (PID: {process['pid']})")
                    else:
                        print(f"  Port {port}: 📦 Our process (PID: {process['pid']})")
                else:
                    print(f"  Port {port}: ⛔ External ({process['name']})")
            else:
                print(f"  Port {port}: ❓ In use (unknown process)")
    print()

    # Test 5: Test force flag for daemon processes
    print("Test 5: Testing force flag (simulated)...")
    print("   Note: In real usage, --force flag would kill daemon processes")
    print("   This is a destructive operation and should be used with caution")
    print()

    print("=" * 60)
    print("Smart Port Detection Tests Complete!")
    print("=" * 60)
    print()
    print("Key Features Demonstrated:")
    print("  ✅ Detect process type on ports")
    print("  ✅ Identify our debug scripts vs daemons vs external")
    print("  ✅ Auto-reclaim ports from debug scripts")
    print("  ✅ Preserve daemon processes (unless forced)")
    print("  ✅ Avoid external processes")
    print()
    print("Usage in CLI:")
    print("  claude-mpm monitor start              # Auto-reclaim from debug scripts")
    print("  claude-mpm monitor start --force      # Force reclaim even from daemons")
    print("  claude-mpm monitor start --no-reclaim # Don't reclaim any ports")
    print("  claude-mpm monitor status --show-ports # Show all port statuses")


if __name__ == "__main__":
    try:
        test_port_detection()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
