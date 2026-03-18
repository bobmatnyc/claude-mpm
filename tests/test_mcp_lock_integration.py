#!/usr/bin/env python3
"""
Integration Test for MCP Lock Management
=========================================

End-to-end test to verify that the MCP gateway properly handles
stale locks and can recover from crashed instances.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_stale_lock_recovery():
    """Test that MCP can recover from stale locks."""

    print("MCP Lock Recovery Integration Test")
    print("=" * 50)

    # Clean up any existing locks first
    cleanup_script = Path(__file__).parent.parent / "scripts" / "cleanup_mcp_locks.py"

    print("\n1. Cleaning up any existing locks...")
    result = subprocess.run(
        [sys.executable, str(cleanup_script), "--force"],
        capture_output=True,
        text=True,
        check=False,
    )
    print(
        f"   Cleanup result: {'✅ Success' if result.returncode == 0 else '❌ Failed'}"
    )

    # Create a fake stale lock (simulate crashed process)
    state_dir = Path.home() / ".claude-mpm" / "mcp"
    state_dir.mkdir(parents=True, exist_ok=True)

    lock_file = state_dir / "gateway.lock"
    instance_file = state_dir / "gateway.json"

    print("\n2. Creating simulated stale lock files...")

    # Use a definitely dead PID
    dead_pid = 99999
    lock_file.write_text(str(dead_pid))

    instance_data = {
        "pid": dead_pid,
        "gateway_name": "test-crashed-gateway",
        "version": "1.0.0",
        "started_at": str(time.time()),
    }
    instance_file.write_text(json.dumps(instance_data))

    print(f"   Created lock file with PID {dead_pid}")
    print(f"   Created instance file: {instance_data['gateway_name']}")

    # Check status - should show stale locks
    print("\n3. Checking lock status (should show stale)...")
    result = subprocess.run(
        [sys.executable, str(cleanup_script), "--check-only"],
        capture_output=True,
        text=True,
        check=False,
    )

    if "stale" in result.stdout.lower():
        print("   ✅ Correctly detected stale locks")
    else:
        print("   ❌ Failed to detect stale locks")
        print(result.stdout)
        return False

    # Test Python-based recovery
    print("\n4. Testing automatic recovery via Python API...")

    try:
        from claude_mpm.services.mcp_gateway.manager import MCPGatewayManager

        manager = MCPGatewayManager()

        # Check initial state
        info = manager.get_running_instance_info()
        if info:
            print(f"   ⚠️  Found existing instance info (PID: {info.get('pid')})")

        # Try to acquire lock (should clean up stale and succeed)
        if manager.acquire_lock():
            print("   ✅ Successfully acquired lock after cleanup")
            manager.release_lock()
        else:
            print("   ❌ Failed to acquire lock")
            return False

    except Exception as e:
        print(f"   ❌ Error during Python API test: {e}")
        return False

    # Verify cleanup happened
    print("\n5. Verifying automatic cleanup...")

    if not lock_file.exists() and not instance_file.exists():
        print("   ✅ Stale files were automatically cleaned")
    else:
        print("   ❌ Stale files still exist")
        if lock_file.exists():
            print(f"      Lock file still exists: {lock_file}")
        if instance_file.exists():
            print(f"      Instance file still exists: {instance_file}")
        return False

    # Test concurrent access prevention
    print("\n6. Testing concurrent access prevention...")

    try:
        manager1 = MCPGatewayManager()
        manager2 = MCPGatewayManager()

        # First manager acquires lock
        if manager1.acquire_lock():
            print("   ✅ First manager acquired lock")

            # Second manager should fail
            if not manager2.acquire_lock():
                print("   ✅ Second manager correctly blocked")
            else:
                print("   ❌ Second manager incorrectly acquired lock")
                manager2.release_lock()
                manager1.release_lock()
                return False

            # Release first lock
            manager1.release_lock()

            # Now second should succeed
            if manager2.acquire_lock():
                print("   ✅ Second manager acquired lock after release")
                manager2.release_lock()
            else:
                print("   ❌ Second manager failed to acquire after release")
                return False
        else:
            print("   ❌ First manager failed to acquire lock")
            return False

    except Exception as e:
        print(f"   ❌ Error during concurrent access test: {e}")
        return False

    # Final cleanup
    print("\n7. Final cleanup...")
    result = subprocess.run(
        [sys.executable, str(cleanup_script), "--force"],
        capture_output=True,
        text=True,
        check=False,
    )
    print(
        f"   Cleanup result: {'✅ Success' if result.returncode == 0 else '❌ Failed'}"
    )

    print("\n" + "=" * 50)
    print("✅ All integration tests passed!")
    print("MCP gateway lock management is working correctly.")

    return True


def test_cleanup_script_cli():
    """Test the cleanup script CLI functionality."""

    print("\nMCP Cleanup Script CLI Test")
    print("=" * 50)

    cleanup_script = Path(__file__).parent.parent / "scripts" / "cleanup_mcp_locks.py"

    # Test help output
    print("\n1. Testing help output...")
    result = subprocess.run(
        [sys.executable, str(cleanup_script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    if "cleanup" in result.stdout.lower() and result.returncode == 0:
        print("   ✅ Help output works")
    else:
        print("   ❌ Help output failed")
        return False

    # Test check-only mode
    print("\n2. Testing check-only mode...")
    result = subprocess.run(
        [sys.executable, str(cleanup_script), "--check-only"],
        capture_output=True,
        text=True,
        check=False,
    )

    if "MCP Lock Status Check" in result.stdout and result.returncode == 0:
        print("   ✅ Check-only mode works")
    else:
        print("   ❌ Check-only mode failed")
        return False

    # Test verbose mode
    print("\n3. Testing verbose mode...")
    result = subprocess.run(
        [sys.executable, str(cleanup_script), "--check-only", "--verbose"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        print("   ✅ Verbose mode works")
    else:
        print("   ❌ Verbose mode failed")
        return False

    print("\n✅ CLI tests passed!")
    return True


def main():
    """Run all integration tests."""

    print("\n" + "=" * 60)
    print("MCP LOCK MANAGEMENT INTEGRATION TESTS")
    print("=" * 60)

    all_passed = True

    # Test stale lock recovery
    if not test_stale_lock_recovery():
        all_passed = False
        print("\n❌ Stale lock recovery test failed")

    # Test cleanup script CLI
    if not test_cleanup_script_cli():
        all_passed = False
        print("\n❌ Cleanup script CLI test failed")

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("The MCP gateway lock management system is working correctly.")
        return 0
    print("❌ SOME TESTS FAILED")
    print("Please review the output above for details.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
