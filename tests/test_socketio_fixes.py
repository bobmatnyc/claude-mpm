#!/usr/bin/env python3
"""
Test script to verify SocketIO daemon fixes.

This script tests:
1. Python environment detection and usage
2. Event loop initialization without race conditions
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Add src to path for imports
script_dir = Path(__file__).parent
src_dir = script_dir.parent / "src"
sys.path.insert(0, str(src_dir))


def test_python_environment_detection():
    """Test that the daemon detects and uses the correct Python environment."""
    print("\n" + "=" * 60)
    print("TEST 1: Python Environment Detection")
    print("=" * 60)

    # Import the daemon module
    from claude_mpm.scripts.socketio_daemon import PYTHON_EXECUTABLE

    print(f"Current Python: {sys.executable}")
    print(f"Detected Python for daemon: {PYTHON_EXECUTABLE}")

    # Check if we're in a virtual environment
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    venv_env = os.environ.get("VIRTUAL_ENV")

    print(f"In virtual environment: {in_venv}")
    print(f"VIRTUAL_ENV variable: {venv_env}")

    # Verify the detection is correct
    if in_venv or venv_env:
        # We should detect the venv Python
        if "venv" in PYTHON_EXECUTABLE or sys.executable == PYTHON_EXECUTABLE:
            print("✅ PASS: Virtual environment Python correctly detected")
            return True
        print("❌ FAIL: Virtual environment not properly detected")
        print(f"   Expected venv Python, got: {PYTHON_EXECUTABLE}")
        return False
    print("✅ PASS: Using system Python (no venv detected)")
    return True


def test_event_loop_initialization():
    """Test that the event loop is properly initialized without race conditions."""
    print("\n" + "=" * 60)
    print("TEST 2: Event Loop Initialization")
    print("=" * 60)

    try:
        from claude_mpm.services.socketio.server.main import SocketIOServer

        # Create server instance
        server = SocketIOServer(
            host="localhost", port=18765
        )  # Use different port for testing
        print("Created SocketIO server instance")

        # Start the server (this should handle the race condition)
        print("Starting server (testing race condition handling)...")
        start_time = time.time()

        try:
            server.start_sync()
            elapsed = time.time() - start_time
            print(f"Server started in {elapsed:.2f}s")

            # Check that the event loop is properly initialized
            if server.core.loop is not None:
                print("✅ Event loop is initialized")
            else:
                print("❌ Event loop is None after start")
                return False

            # Check that broadcaster has the loop reference
            if server.broadcaster and server.broadcaster.loop is not None:
                print("✅ Broadcaster has event loop reference")
            else:
                print("❌ Broadcaster missing event loop reference")
                return False

            # Check server is running
            if server.running and server.core.running:
                print("✅ Server is running")
            else:
                print("❌ Server not properly running")
                return False

            print("✅ PASS: Event loop initialized without race condition")

            # Clean shutdown
            print("Stopping server...")
            server.stop_sync()
            print("Server stopped cleanly")

            return True

        except Exception as e:
            print(f"❌ FAIL: Error during server start: {e}")
            import traceback

            traceback.print_exc()
            return False

    except ImportError as e:
        print(f"⚠️  SKIP: Cannot import SocketIOServer: {e}")
        print("   This may be expected if socketio dependencies are not installed")
        return None


def test_daemon_subprocess():
    """Test that the daemon can be started as a subprocess with correct Python."""
    print("\n" + "=" * 60)
    print("TEST 3: Daemon Subprocess Execution")
    print("=" * 60)

    daemon_script = src_dir / "claude_mpm" / "scripts" / "socketio_daemon.py"

    if not daemon_script.exists():
        print(f"❌ Daemon script not found at: {daemon_script}")
        return False

    try:
        # Test that we can get the status (doesn't start the server)
        result = subprocess.run(
            [sys.executable, str(daemon_script), "status"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        print(f"Status command exit code: {result.returncode}")
        if "Socket.IO daemon server is" in result.stdout:
            print("✅ Daemon script executes correctly")
            print(f"   Output: {result.stdout.strip()}")
            return True
        print("❌ Unexpected daemon output")
        print(f"   stdout: {result.stdout}")
        print(f"   stderr: {result.stderr}")
        return False

    except subprocess.TimeoutExpired:
        print("❌ FAIL: Daemon script timed out")
        return False
    except Exception as e:
        print(f"❌ FAIL: Error running daemon: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SocketIO Daemon Fix Verification")
    print("=" * 60)

    results = []

    # Test 1: Python environment detection
    results.append(
        ("Python Environment Detection", test_python_environment_detection())
    )

    # Test 2: Event loop initialization
    result = test_event_loop_initialization()
    if result is not None:
        results.append(("Event Loop Initialization", result))

    # Test 3: Daemon subprocess
    results.append(("Daemon Subprocess", test_daemon_subprocess()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)

    for name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
