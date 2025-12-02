#!/usr/bin/env python3
"""Test script to verify that the configuration success message only appears once."""

import logging
import sys
from pathlib import Path

# Add parent directory to path to import claude_mpm
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up logging to capture all messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

# Track log messages for verification
success_messages = []
original_info = logging.Logger.info


def patched_info(self, msg, *args, **kwargs):
    """Patched info method to track success messages."""
    if "Successfully loaded configuration" in str(msg):
        success_messages.append(msg)
    return original_info(self, msg, *args, **kwargs)


# Patch the logging to track messages
logging.Logger.info = patched_info

# Now test the Config singleton


def test_single_success_message():
    """Test that the success message only appears once."""
    global success_messages
    success_messages = []

    # Reset singleton for clean test
    Config.reset_singleton()

    print("\n=== Test 1: Multiple Config instantiations ===")

    # First instantiation
    config1 = Config()
    print(f"Config 1 created: {config1}")

    # Second instantiation (should reuse singleton)
    config2 = Config()
    print(f"Config 2 created: {config2}")

    # Third instantiation (should reuse singleton)
    config3 = Config()
    print(f"Config 3 created: {config3}")

    # Verify they're all the same instance
    assert config1 is config2 is config3, (
        "Config instances should be the same (singleton)"
    )

    # Check how many success messages were logged
    print(f"\nSuccess messages logged: {len(success_messages)}")
    for i, msg in enumerate(success_messages, 1):
        print(f"  {i}. {msg}")

    if len(success_messages) == 0:
        print("✓ No duplicate messages (no config file found)")
        return True
    if len(success_messages) == 1:
        print("✓ SUCCESS: Only one configuration success message logged!")
        return True
    print(
        f"✗ FAILURE: {len(success_messages)} success messages logged (expected 0 or 1)"
    )
    return False


def test_with_explicit_config_file():
    """Test with explicit config file paths."""
    global success_messages
    success_messages = []

    # Reset singleton for clean test
    Config.reset_singleton()

    print("\n=== Test 2: Explicit config file paths ===")

    config_file = Path.cwd() / ".claude-mpm" / "configuration.yaml"

    if config_file.exists():
        # First instantiation with explicit file
        config1 = Config(config_file=config_file)
        print(f"Config 1 created with explicit file: {config1}")

        # Second instantiation with same file (should be ignored)
        config2 = Config(config_file=config_file)
        print(f"Config 2 created with same file: {config2}")

        # Third instantiation with no file (should use existing)
        config3 = Config()
        print(f"Config 3 created with no file: {config3}")

        # Check how many success messages were logged
        print(f"\nSuccess messages logged: {len(success_messages)}")
        for i, msg in enumerate(success_messages, 1):
            print(f"  {i}. {msg}")

        if len(success_messages) == 1:
            print("✓ SUCCESS: Only one configuration success message logged!")
            return True
        print(
            f"✗ FAILURE: {len(success_messages)} success messages logged (expected 1)"
        )
        return False
    print(f"Config file not found at {config_file}, skipping test")
    return True


def main():
    """Run all tests."""
    print("Testing configuration duplicate message fix...")
    print("=" * 60)

    # Run tests
    test1_pass = test_single_success_message()
    test2_pass = test_with_explicit_config_file()

    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print(f"  Test 1 (Multiple instantiations): {'PASS' if test1_pass else 'FAIL'}")
    print(f"  Test 2 (Explicit config files): {'PASS' if test2_pass else 'FAIL'}")

    all_pass = test1_pass and test2_pass
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_pass else '✗ SOME TESTS FAILED'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
