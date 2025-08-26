#!/usr/bin/env python3
"""Comprehensive test to identify duplicate configuration logging during startup."""

import io
import logging
import sys
from pathlib import Path

# Capture all logs to analyze them
log_capture = io.StringIO()

# Setup logging to capture everything
logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s: %(message)s", stream=log_capture
)

# Also setup a console handler to see output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logging.getLogger().addHandler(console_handler)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_full_startup_sequence():
    """Test the full startup sequence as it happens in real usage."""

    print("=== Testing full startup sequence ===\n")

    # Import and create the ClaudeRunner which initializes all services
    print("1. Creating ClaudeRunner (this initializes all services)...")
    from claude_mpm.core.claude_runner import ClaudeRunner

    # Reset singleton for clean test

    Config.reset_singleton()

    # Create runner which should initialize everything
    ClaudeRunner(
        enable_tickets=False,
        log_level="OFF",
        claude_args=[],
        launch_method="exec",
        enable_websocket=False,
    )

    print("\n2. Checking for duplicate configuration messages...")

    # Get all log messages
    log_contents = log_capture.getvalue()

    # Count occurrences of the success message
    success_message = "Successfully loaded configuration"
    success_count = log_contents.count(success_message)

    print(f"\nSuccess message count: {success_count}")

    if success_count > 1:
        print("\n⚠️  DUPLICATE MESSAGES FOUND!")
        print("Here are all occurrences:")
        for i, line in enumerate(log_contents.split("\n"), 1):
            if success_message in line:
                print(f"  Line {i}: {line}")
    else:
        print("✅ No duplicate messages found - singleton is working correctly")

    # Also check for Config instance creation
    create_count = log_contents.count("Creating new Config singleton")
    reuse_count = log_contents.count("Reusing existing Config singleton")

    print("\nConfig creation stats:")
    print(f"  - New singleton created: {create_count} time(s)")
    print(f"  - Singleton reused: {reuse_count} time(s)")

    # Show any warnings or errors
    error_lines = [
        line
        for line in log_contents.split("\n")
        if "ERROR" in line or "WARNING" in line
    ]
    if error_lines:
        print("\n⚠️  Warnings/Errors found:")
        for line in error_lines[:5]:  # Show first 5
            print(f"  {line}")

    return success_count == 1


def test_parallel_initialization():
    """Test if parallel service initialization might cause issues."""
    import threading

    print("\n=== Testing parallel initialization ===\n")

    # Reset for clean test
    Config.reset_singleton()

    configs = []

    def create_config():
        configs.append(Config())

    # Create multiple threads that all try to create Config
    threads = []
    for _i in range(5):
        t = threading.Thread(target=create_config)
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    # Check if all got the same instance
    all_same = all(c is configs[0] for c in configs)
    print(f"All threads got same instance: {all_same}")

    # Check log for duplicate messages
    log_contents = log_capture.getvalue()
    success_count = log_contents.count("Successfully loaded configuration")
    print(f"Success message count in parallel test: {success_count}")

    return all_same and success_count <= 2  # Allow 2 since we reset


if __name__ == "__main__":
    # Clear log capture between tests
    success1 = test_full_startup_sequence()

    # Clear and test parallel
    log_capture.truncate(0)
    log_capture.seek(0)
    success2 = test_parallel_initialization()

    print("\n=== Final Results ===")
    print(f"Full startup test: {'PASSED' if success1 else 'FAILED'}")
    print(f"Parallel init test: {'PASSED' if success2 else 'FAILED'}")

    if success1 and success2:
        print("\n✅ All tests passed - no duplicate configuration loading detected")
    else:
        print("\n❌ Some tests failed - investigation needed")
