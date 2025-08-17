#!/usr/bin/env python3
"""Test script for MemoryGuardian service.

This script demonstrates the MemoryGuardian service functionality by:
1. Starting a subprocess that consumes memory
2. Monitoring its memory usage
3. Demonstrating restart when thresholds are exceeded
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.config.memory_guardian_config import MemoryGuardianConfig
from claude_mpm.services.infrastructure.memory_guardian import MemoryGuardian


def create_memory_consumer_script():
    """Create a Python script that consumes memory over time."""
    script = """
import time
import sys

# Allocate memory in chunks
data = []
chunk_size = 10 * 1024 * 1024  # 10MB chunks
total_allocated = 0

print(f"Memory consumer started (PID: {os.getpid()})", flush=True)

try:
    while True:
        # Allocate a chunk
        chunk = bytearray(chunk_size)
        data.append(chunk)
        total_allocated += chunk_size

        print(f"Allocated: {total_allocated / (1024*1024):.2f}MB", flush=True)

        # Sleep to simulate work
        time.sleep(2)

        # Exit after allocating 500MB for demo
        if total_allocated > 500 * 1024 * 1024:
            print("Reached allocation limit, exiting", flush=True)
            break

except KeyboardInterrupt:
    print("Memory consumer interrupted", flush=True)
    sys.exit(0)
"""

    # Write script to temp file
    script_path = Path("/tmp/memory_consumer.py")
    script_path.write_text(script)
    return str(script_path)


async def test_basic_functionality():
    """Test basic MemoryGuardian functionality."""
    print("=" * 60)
    print("Testing Basic MemoryGuardian Functionality")
    print("=" * 60)

    # Create configuration with low thresholds for testing
    config = MemoryGuardianConfig()
    config.thresholds.warning = 100  # 100MB
    config.thresholds.critical = 200  # 200MB
    config.thresholds.emergency = 300  # 300MB
    config.monitoring.normal_interval = 2  # Check every 2 seconds
    config.monitoring.detailed_logging = True

    # Use a simple sleep command for testing
    config.process_command = [sys.executable, "-c", "import time; time.sleep(30)"]

    # Create guardian
    guardian = MemoryGuardian(config)

    try:
        # Initialize
        print("\n1. Initializing MemoryGuardian...")
        success = await guardian.initialize()
        print(f"   Initialization: {'✓' if success else '✗'}")

        # Check status
        print("\n2. Checking status...")
        status = guardian.get_status()
        print(f"   Process state: {status['process']['state']}")
        print(f"   Memory state: {status['memory']['state']}")
        print(f"   Monitoring active: {status['monitoring']['active']}")

        # Monitor for a bit
        print("\n3. Monitoring for 10 seconds...")
        await asyncio.sleep(10)

        # Check memory stats
        print("\n4. Memory statistics:")
        status = guardian.get_status()
        print(f"   Current: {status['memory']['current_mb']:.2f}MB")
        print(f"   Peak: {status['memory']['peak_mb']:.2f}MB")
        print(f"   Average: {status['memory']['average_mb']:.2f}MB")
        print(f"   Samples: {status['monitoring']['samples']}")

    finally:
        # Shutdown
        print("\n5. Shutting down...")
        await guardian.shutdown()
        print("   Shutdown complete")


async def test_memory_monitoring():
    """Test memory monitoring with a memory-consuming process."""
    print("\n" + "=" * 60)
    print("Testing Memory Monitoring with Consumer Process")
    print("=" * 60)

    # Create memory consumer script
    script_path = create_memory_consumer_script()

    # Create configuration
    config = MemoryGuardianConfig()
    config.thresholds.warning = 50  # 50MB
    config.thresholds.critical = 100  # 100MB
    config.thresholds.emergency = 200  # 200MB
    config.monitoring.normal_interval = 1
    config.monitoring.warning_interval = 0.5
    config.monitoring.detailed_logging = True
    config.process_command = [sys.executable, script_path]

    # Create guardian
    guardian = MemoryGuardian(config)

    try:
        # Initialize and start
        print("\n1. Starting memory consumer process...")
        await guardian.initialize()

        # Monitor for a while
        print("\n2. Monitoring memory usage...")
        for i in range(30):
            await asyncio.sleep(2)

            status = guardian.get_status()
            memory_mb = status["memory"]["current_mb"]
            state = status["memory"]["state"]

            # Print status with appropriate symbol
            symbol = (
                "✓"
                if state == "normal"
                else "⚠"
                if state == "warning"
                else "⚡"
                if state == "critical"
                else "🔥"
            )
            print(
                f"   [{i+1:2d}] Memory: {memory_mb:6.2f}MB | State: {state:9s} {symbol}"
            )

            # Check if process was restarted
            if status["restarts"]["total"] > 0:
                print(
                    f"\n   ↻ Process restarted! Total restarts: {status['restarts']['total']}"
                )
                break

        # Final statistics
        print("\n3. Final statistics:")
        status = guardian.get_status()
        print(f"   Peak memory: {status['memory']['peak_mb']:.2f}MB")
        print(f"   Total restarts: {status['restarts']['total']}")
        print(f"   Process uptime: {status['process']['uptime_seconds']:.2f}s")

    finally:
        await guardian.shutdown()
        Path(script_path).unlink(missing_ok=True)


async def test_restart_policy():
    """Test restart policy and cooldowns."""
    print("\n" + "=" * 60)
    print("Testing Restart Policy")
    print("=" * 60)

    config = MemoryGuardianConfig()
    config.restart_policy.max_attempts = 3
    config.restart_policy.attempt_window = 60
    config.restart_policy.initial_cooldown = 2
    config.restart_policy.cooldown_multiplier = 2.0

    # Use a process that exits immediately to test restart
    config.process_command = [sys.executable, "-c", "import sys; sys.exit(1)"]
    config.auto_start = True

    guardian = MemoryGuardian(config)

    try:
        print("\n1. Testing restart attempts...")
        await guardian.initialize()

        # Monitor and let it try to restart
        for i in range(5):
            await asyncio.sleep(3)
            status = guardian.get_status()

            print(f"\n   Attempt {i+1}:")
            print(f"   - Process state: {status['process']['state']}")
            print(f"   - Total restarts: {status['restarts']['total']}")
            print(f"   - Can restart: {status['restarts']['can_restart']}")
            print(
                f"   - Consecutive failures: {status['restarts']['consecutive_failures']}"
            )

            if not status["restarts"]["can_restart"]:
                print("\n   ✗ Maximum restart attempts reached!")
                break

    finally:
        await guardian.shutdown()


async def test_state_hooks():
    """Test state preservation hooks."""
    print("\n" + "=" * 60)
    print("Testing State Preservation Hooks")
    print("=" * 60)

    saved_states = []

    def save_hook(state):
        """Hook to save state."""
        saved_states.append(state)
        print(
            f"   State saved: PID={state.get('process_pid')}, "
            f"Memory={state['memory_stats']['current_mb']:.2f}MB"
        )

    def restore_hook(state):
        """Hook to restore state."""
        print(f"   State restored: Restarts={state.get('total_restarts')}")

    config = MemoryGuardianConfig()
    config.process_command = [sys.executable, "-c", "import time; time.sleep(10)"]

    guardian = MemoryGuardian(config)
    guardian.add_state_save_hook(save_hook)
    guardian.add_state_restore_hook(restore_hook)

    try:
        print("\n1. Starting process with hooks...")
        await guardian.initialize()

        print("\n2. Triggering restart...")
        await guardian.restart_process("Test restart with hooks")

        print(f"\n3. States captured: {len(saved_states)}")

    finally:
        await guardian.shutdown()


async def main():
    """Run all tests."""
    print("MemoryGuardian Service Test Suite")
    print("=" * 60)

    try:
        # Test basic functionality
        await test_basic_functionality()

        # Test memory monitoring (commented out by default as it takes time)
        # await test_memory_monitoring()

        # Test restart policy
        await test_restart_policy()

        # Test state hooks
        await test_state_hooks()

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("This script requires Python 3.8 or later")
        sys.exit(1)

    # Add missing import
    import os

    # Run tests
    asyncio.run(main())
