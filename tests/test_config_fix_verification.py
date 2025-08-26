#!/usr/bin/env python3
"""Comprehensive verification that the config duplicate message fix works."""

import logging
import subprocess
import sys
import tempfile
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def test_thread_safety():
    """Test thread safety of the singleton."""
    import threading

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    # Reset for clean test
    Config.reset_singleton()

    configs = []
    success_messages = []

    def create_config(name):
        """Create a config instance in a thread."""
        config = Config()
        configs.append((name, id(config)))
        # Check if success was logged
        success_messages.append((name, Config._success_logged))

    # Create threads
    threads = []
    for i in range(10):
        thread = threading.Thread(target=create_config, args=(f"Thread-{i}",))
        threads.append(thread)

    # Start all threads simultaneously
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check results
    unique_ids = {id_val for _, id_val in configs}

    print("\n=== THREAD SAFETY TEST ===")
    print(f"Created {len(configs)} Config instances in threads")
    print(f"Unique instance IDs: {len(unique_ids)}")
    print(f"All same instance: {len(unique_ids) == 1}")
    print(f"Success flag final value: {Config._success_logged}")

    # Count how many threads saw success_logged as False
    saw_false = sum(1 for _, logged in success_messages if not logged)
    print(f"Threads that saw _success_logged=False: {saw_false}")

    return len(unique_ids) == 1 and saw_false <= 1


def test_import_order():
    """Test different import orders."""
    test_script = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up logging to capture messages
import logging
import io
log_stream = io.StringIO()
handler = logging.StreamHandler(log_stream)
handler.setLevel(logging.INFO)
logging.getLogger("claude_mpm.core.config").addHandler(handler)

# Import in different orders
from claude_mpm.services.hook_service import HookService
from claude_mpm.utils.config_manager import ConfigurationManager as ConfigManager
from claude_mpm.services.event_aggregator import EventAggregator

# Create instances
hook = HookService()
config = Config()
aggregator = EventAggregator()

# Check log output
log_output = log_stream.getvalue()
success_count = log_output.count("Successfully loaded configuration")
print(f"Success messages: {success_count}")

# Verify singleton
print(f"All configs same: {id(config) == id(hook.config) if hasattr(hook, 'config') else 'N/A'}")
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_script)
        test_file = f.name

    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        print("\n=== IMPORT ORDER TEST ===")
        print(result.stdout)

        # Check for single success message
        return (
            "Success messages: 1" in result.stdout
            or "Success messages: 0" in result.stdout
        )

    finally:
        Path(test_file).unlink()


def main():
    """Run comprehensive verification tests."""
    print("=" * 70)
    print("CONFIG DUPLICATE MESSAGE FIX VERIFICATION")
    print("=" * 70)

    all_passed = True

    # Test 1: Thread safety
    print("\nTest 1: Thread Safety")
    try:
        if test_thread_safety():
            print("✓ Thread safety test PASSED")
        else:
            print("✗ Thread safety test FAILED")
            all_passed = False
    except Exception as e:
        print(f"✗ Thread safety test ERROR: {e}")
        all_passed = False

    # Test 2: Import order
    print("\nTest 2: Import Order")
    try:
        if test_import_order():
            print("✓ Import order test PASSED")
        else:
            print("✗ Import order test FAILED")
            all_passed = False
    except Exception as e:
        print(f"✗ Import order test ERROR: {e}")
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("✓✓✓ ALL VERIFICATION TESTS PASSED ✓✓✓")
        print("The config duplicate message fix is working correctly!")
    else:
        print("✗✗✗ SOME VERIFICATION TESTS FAILED ✗✗✗")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
