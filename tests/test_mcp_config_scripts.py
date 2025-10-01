#!/usr/bin/env python3
"""
Test script to verify MCP configuration scripts maintain valid JSON.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_json_validity(config_path: Path) -> bool:
    """Test if a JSON file is valid.

    Args:
        config_path: Path to JSON file

    Returns:
        True if valid JSON, False otherwise
    """
    try:
        with config_path.open() as f:
            json.load(f)
        return True
    except (OSError, json.JSONDecodeError) as e:
        print(f"❌ Invalid JSON: {e}")
        return False


def test_registration_script():
    """Test the register_mcp_gateway.py script."""
    print("\n🧪 Testing register_mcp_gateway.py...")

    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        test_config = {
            "mcpServers": {"test-server": {"command": "test", "args": ["arg1", "arg2"]}}
        }
        json.dump(test_config, tmp)
        tmp_path = Path(tmp.name)

    try:
        # Test dry-run
        result = subprocess.run(
            [
                sys.executable,
                "scripts/register_mcp_gateway.py",
                "--dry-run",
                "--config-path",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"❌ Dry-run failed: {result.stderr}")
            return False

        # Test actual registration
        result = subprocess.run(
            [
                sys.executable,
                "scripts/register_mcp_gateway.py",
                "--config-path",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"❌ Registration failed: {result.stderr}")
            return False

        # Verify JSON is still valid
        if not test_json_validity(tmp_path):
            print("❌ JSON became invalid after registration")
            return False

        # Verify the gateway was added
        with tmp_path.open() as f:
            config = json.load(f)
            if "claude-mpm-gateway" not in config.get("mcpServers", {}):
                print("❌ Gateway not added to config")
                return False

        print("✅ Registration script tests passed")
        return True

    finally:
        # Clean up
        tmp_path.unlink(missing_ok=True)
        # Clean up any backups created
        backup_dir = tmp_path.parent / "backups"
        if backup_dir.exists():
            for backup in backup_dir.glob("*.json"):
                backup.unlink()
            backup_dir.rmdir()


def test_restore_script():
    """Test the restore_mcp_config.py script."""
    print("\n🧪 Testing restore_mcp_config.py...")

    # Test listing (should not fail even if no backups)
    result = subprocess.run(
        [sys.executable, "scripts/restore_mcp_config.py", "--list"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"❌ List command failed: {result.stderr}")
        return False

    # Test comparison
    result = subprocess.run(
        [sys.executable, "scripts/restore_mcp_config.py", "--compare"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"❌ Compare command failed: {result.stderr}")
        return False

    print("✅ Restore script tests passed")
    return True


def main():
    """Run all tests."""
    print("🔬 Testing MCP Configuration Scripts")
    print("=" * 50)

    all_passed = True

    # Test registration script
    if not test_registration_script():
        all_passed = False

    # Test restore script
    if not test_restore_script():
        all_passed = False

    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All tests passed!")
        return 0
    print("❌ Some tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
