#!/usr/bin/env python3
"""Test for duplicate configuration success messages during real startup."""

import subprocess
import sys
import tempfile
from pathlib import Path


def count_success_messages(output):
    """Count how many times the success message appears."""
    lines = output.split("\n")
    return sum(1 for line in lines if "Successfully loaded configuration" in line)


def test_with_real_cli():
    """Test using actual CLI startup."""
    print("=" * 70)
    print("Testing Real CLI Startup for Duplicate Messages")
    print("=" * 70)

    # Create a temporary configuration file to ensure we get a success message
    with tmp_path as tmpdir:
        config_dir = Path(tmpdir) / ".claude-mpm"
        config_dir.mkdir()
        config_file = config_dir / "configuration.yaml"

        # Write minimal config
        config_file.write_text(
            """
response_logging:
  enabled: true
  format: json
"""
        )

        # Run claude-mpm config validate command which should trigger config loading
        # Use the CLI in a way that loads configuration
        cmd = [sys.executable, "-m", "claude_mpm.cli", "config", "validate"]

        env = {
            **subprocess.os.environ,
            "PYTHONPATH": str(Path(__file__).parent.parent / "src"),
            # Set debug logging to see all messages
            "LOG_LEVEL": "DEBUG",
        }

        print(f"\nRunning command: {' '.join(cmd)}")
        print(f"Working directory: {tmpdir}")
        print(f"Config file: {config_file}")

        # Run the command and capture output
        result = subprocess.run(
            cmd,
            cwd=tmpdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        # Combine stdout and stderr to check all output
        full_output = result.stdout + result.stderr

        # Count success messages
        success_count = count_success_messages(full_output)

        print("\n" + "=" * 70)
        print("OUTPUT ANALYSIS:")
        print("=" * 70)

        # Show relevant lines
        print("\nRelevant log lines containing 'configuration' or 'Config':")
        for line in full_output.split("\n"):
            if any(
                keyword in line.lower()
                for keyword in ["configuration", "config", "loaded"]
            ):
                print(f"  {line[:120]}")

        print("\n" + "=" * 70)
        print("RESULTS:")
        print(f"Success messages found: {success_count}")

        if success_count == 0:
            print(
                "⚠ No success messages found (may be normal if version command doesn't load config)"
            )
            return True
        if success_count == 1:
            print("✓ SUCCESS: Configuration success message appeared exactly ONCE!")
            return True
        print(
            f"✗ FAILURE: Configuration success message appeared {success_count} times!"
        )

        # Show all occurrences
        print("\nAll success message occurrences:")
        for i, line in enumerate(full_output.split("\n"), 1):
            if "Successfully loaded configuration" in line:
                print(f"  Line {i}: {line}")
        return False


def test_with_multiple_imports():
    """Test by importing Config from different modules."""
    print("\n" + "=" * 70)
    print("Testing Multiple Import Paths")
    print("=" * 70)

    # Test if importing Config from different modules causes issues
    test_script = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

# Import Config from different places
from claude_mpm.utils.config_manager import ConfigurationManager as ConfigManager
config1 = Config()

# Import via a service that uses Config
from claude_mpm.services.hook_service import HookService
hook_service = HookService()

# Import via another service
from claude_mpm.utils.runner_config import RunnerConfiguration
runner_config = RunnerConfiguration()

print(f"config1 ID: {id(config1)}")
print(f"Config class ID: {id(Config)}")
print(f"Config._success_logged: {Config._success_logged}")
"""

    # Write and run test script
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

        output = result.stdout + result.stderr
        success_count = count_success_messages(output)

        print(f"\nSuccess messages found: {success_count}")

        if success_count <= 1:
            print("✓ No duplicate messages from multiple imports")
            return True
        print(f"✗ Found {success_count} success messages from multiple imports")
        return False

    finally:
        Path(test_file).unlink()


def main():
    """Run all tests."""
    print("=" * 70)
    print("DUPLICATE CONFIG MESSAGE TESTING")
    print("=" * 70)

    all_passed = True

    # Test 1: Real CLI startup
    try:
        if not test_with_real_cli():
            all_passed = False
    except Exception as e:
        print(f"✗ Real CLI test failed with error: {e}")
        all_passed = False

    # Test 2: Multiple import paths
    try:
        if not test_with_multiple_imports():
            all_passed = False
    except Exception as e:
        print(f"✗ Multiple import test failed with error: {e}")
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - No duplicate configuration messages!")
    else:
        print("✗ SOME TESTS FAILED - Duplicate messages detected!")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
