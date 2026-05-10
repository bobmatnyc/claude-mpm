#!/usr/bin/env python3
"""Test script to verify that the configuration success message only appears once."""

import logging
import sys
from pathlib import Path

from claude_mpm.core.config import Config

# Add parent directory to path to import claude_mpm
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up logging to capture all messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)


def _make_patched_info(success_messages, original_info):
    """Return a patched Logger.info that appends to success_messages."""

    def patched_info(self, msg, *args, **kwargs):
        if "Successfully loaded configuration" in str(msg):
            success_messages.append(msg)
        return original_info(self, msg, *args, **kwargs)

    return patched_info


def test_single_success_message(monkeypatch):
    """Test that the success message only appears once."""
    success_messages = []
    original_info = logging.Logger.info
    monkeypatch.setattr(
        logging.Logger, "info", _make_patched_info(success_messages, original_info)
    )

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

    assert len(success_messages) <= 1, (
        f"Expected 0 or 1 success messages, got {len(success_messages)}"
    )

    if len(success_messages) == 0:
        print("✓ No duplicate messages (no config file found)")
    else:
        print("✓ SUCCESS: Only one configuration success message logged!")


def test_with_explicit_config_file(monkeypatch):
    """Test with explicit config file paths."""
    success_messages = []
    original_info = logging.Logger.info
    monkeypatch.setattr(
        logging.Logger, "info", _make_patched_info(success_messages, original_info)
    )

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

        assert len(success_messages) == 1, (
            f"Expected exactly 1 success message, got {len(success_messages)}"
        )
        print("✓ SUCCESS: Only one configuration success message logged!")
    else:
        print(f"Config file not found at {config_file}, skipping test")


def main():
    """Run all tests (for direct script execution)."""
    print("Testing configuration duplicate message fix...")
    print("=" * 60)

    success_messages_1 = []
    original_info = logging.Logger.info
    logging.Logger.info = _make_patched_info(success_messages_1, original_info)
    try:
        Config.reset_singleton()
        config1 = Config()
        config2 = Config()
        config3 = Config()
        assert config1 is config2 is config3
        test1_pass = len(success_messages_1) <= 1
    finally:
        logging.Logger.info = original_info

    success_messages_2 = []
    logging.Logger.info = _make_patched_info(success_messages_2, original_info)
    try:
        Config.reset_singleton()
        config_file = Path.cwd() / ".claude-mpm" / "configuration.yaml"
        if config_file.exists():
            Config(config_file=config_file)
            Config(config_file=config_file)
            Config()
            test2_pass = len(success_messages_2) == 1
        else:
            test2_pass = True
    finally:
        logging.Logger.info = original_info

    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print(f"  Test 1 (Multiple instantiations): {'PASS' if test1_pass else 'FAIL'}")
    print(f"  Test 2 (Explicit config files): {'PASS' if test2_pass else 'FAIL'}")

    all_pass = test1_pass and test2_pass
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_pass else '✗ SOME TESTS FAILED'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
