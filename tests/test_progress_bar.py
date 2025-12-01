#!/usr/bin/env python3
"""Test script for progress bar functionality.

WHY: Tests the progress bar utility in various scenarios to ensure correct
operation in both TTY and non-TTY environments.

Usage:
    python scripts/test_progress_bar.py              # Test with auto-detection
    python scripts/test_progress_bar.py --no-tty     # Force non-TTY mode
    python scripts/test_progress_bar.py > log.txt    # Test with redirected output
"""

import argparse
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.progress import ProgressBar, create_progress_bar


def test_basic_progress_bar(enabled=None):
    """Test basic progress bar with manual updates."""
    print("\n=== Test 1: Basic Progress Bar ===")

    total = 20
    pb = create_progress_bar(total=total, prefix="Downloading files", enabled=enabled)

    for i in range(total):
        time.sleep(0.05)  # Simulate work
        pb.update(i + 1, message=f"file_{i:02d}.md")

    pb.finish(message="All files downloaded")
    print("✓ Basic progress bar test completed")


def test_context_manager(enabled=None):
    """Test progress bar as context manager."""
    print("\n=== Test 2: Context Manager ===")

    total = 15
    with ProgressBar(total=total, prefix="Processing items", enabled=enabled) as pb:
        for i in range(total):
            time.sleep(0.05)
            pb.update(i + 1, message=f"item_{i}")

    print("✓ Context manager test completed")


def test_fast_updates(enabled=None):
    """Test progress bar with rapid updates (throttling)."""
    print("\n=== Test 3: Fast Updates (Throttled) ===")

    total = 100
    pb = create_progress_bar(total=total, prefix="Fast processing", enabled=enabled)

    for i in range(total):
        time.sleep(0.001)  # Very fast updates - should be throttled
        pb.update(i + 1, message=f"batch_{i}")

    pb.finish(message="Fast processing complete")
    print("✓ Fast updates test completed")


def test_long_message_truncation(enabled=None):
    """Test progress bar with very long messages (terminal width handling)."""
    print("\n=== Test 4: Long Message Truncation ===")

    total = 10
    pb = create_progress_bar(total=total, prefix="Long messages", enabled=enabled)

    for i in range(total):
        time.sleep(0.1)
        long_message = (
            f"very_long_filename_that_exceeds_terminal_width_{i}_" + "x" * 100
        )
        pb.update(i + 1, message=long_message)

    pb.finish(message="Long message test complete")
    print("✓ Long message truncation test completed")


def test_milestone_logging_non_tty():
    """Test non-TTY mode with milestone logging."""
    print("\n=== Test 5: Non-TTY Milestone Logging ===")

    total = 100
    # Force non-TTY mode
    pb = ProgressBar(total=total, prefix="Non-TTY processing", enabled=False)

    for i in range(total):
        time.sleep(0.01)
        pb.update(i + 1, message=f"item_{i}")

    pb.finish(message="Non-TTY processing complete")
    print("✓ Non-TTY milestone logging test completed")


def test_error_scenario(enabled=None):
    """Test progress bar with exception handling."""
    print("\n=== Test 6: Error Scenario ===")

    total = 20
    try:
        with ProgressBar(
            total=total, prefix="Processing with error", enabled=enabled
        ) as pb:
            for i in range(total):
                time.sleep(0.05)
                pb.update(i + 1, message=f"item_{i}")

                # Simulate error at 50%
                if i == 10:
                    raise ValueError("Simulated error at 50%")
    except ValueError as e:
        print(f"✓ Error handled correctly: {e}")


def test_agent_sync_simulation(enabled=None):
    """Simulate agent sync scenario with progress bar."""
    print("\n=== Test 7: Agent Sync Simulation ===")

    agent_files = [
        "research.md",
        "engineer.md",
        "qa.md",
        "documentation.md",
        "security.md",
        "ops.md",
        "ticketing.md",
        "product_owner.md",
        "version_control.md",
        "project_organizer.md",
    ]

    pb = create_progress_bar(
        total=len(agent_files), prefix="Syncing agents", enabled=enabled
    )

    for idx, agent_file in enumerate(agent_files, start=1):
        time.sleep(0.2)  # Simulate network download
        pb.update(idx, message=agent_file)

    pb.finish(message=f"Complete: {len(agent_files)} agents synced")
    print("✓ Agent sync simulation test completed")


def main():
    """Run all progress bar tests."""
    parser = argparse.ArgumentParser(description="Test progress bar functionality")
    parser.add_argument(
        "--no-tty",
        action="store_true",
        help="Force non-TTY mode (disable progress bars)",
    )
    parser.add_argument("--test", type=int, help="Run specific test only (1-7)")

    args = parser.parse_args()

    # Determine enabled state
    enabled = None if not args.no_tty else False

    print("=" * 60)
    print("Progress Bar Test Suite")
    print("=" * 60)

    if args.no_tty:
        print("Mode: Non-TTY (forced)")
    else:
        print(f"Mode: {'TTY' if sys.stdout.isatty() else 'Non-TTY'} (auto-detected)")

    # Run tests
    tests = [
        test_basic_progress_bar,
        test_context_manager,
        test_fast_updates,
        test_long_message_truncation,
        test_milestone_logging_non_tty,
        test_error_scenario,
        test_agent_sync_simulation,
    ]

    if args.test:
        # Run specific test
        if 1 <= args.test <= len(tests):
            test_func = tests[args.test - 1]
            if test_func == test_milestone_logging_non_tty:
                test_func()  # No enabled parameter
            else:
                test_func(enabled=enabled)
        else:
            print(f"Error: Test {args.test} not found. Valid range: 1-{len(tests)}")
            return 1
    else:
        # Run all tests
        for test_func in tests:
            if test_func == test_milestone_logging_non_tty:
                test_func()  # No enabled parameter
            else:
                test_func(enabled=enabled)

    print("\n" + "=" * 60)
    print("✓ All tests completed successfully")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
