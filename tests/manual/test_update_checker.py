#!/usr/bin/env python3
"""
Manual Test Script for Update Checking System

Run this script to manually test the update checking functionality:
    python tests/manual/test_update_checker.py

This script tests:
1. Version detection (claude-mpm and Claude Code)
2. Installation method detection
3. Update checking against PyPI
4. Configuration loading
5. Notification display
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for development testing
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.core.config import Config
from claude_mpm.services.self_upgrade_service import SelfUpgradeService


async def test_version_detection():
    """Test version detection."""
    print("=" * 70)
    print("TEST 1: Version Detection")
    print("=" * 70)

    service = SelfUpgradeService()

    print(f"✓ Current claude-mpm version: {service.current_version}")
    print(f"✓ Installation method: {service.installation_method}")

    if service.claude_code_version:
        print(f"✓ Claude Code version: {service.claude_code_version}")
    else:
        print("⚠ Claude Code not detected")

    print()


async def test_claude_code_compatibility():
    """Test Claude Code compatibility checking."""
    print("=" * 70)
    print("TEST 2: Claude Code Compatibility")
    print("=" * 70)

    service = SelfUpgradeService()
    compat = service.check_claude_code_compatibility()

    print(f"Installed: {compat['installed']}")
    if compat["installed"]:
        print(f"Version: {compat['version']}")
        print(f"Meets Minimum: {compat['meets_minimum']}")
        print(f"Is Recommended: {compat['is_recommended']}")
        print(f"Status: {compat['status']}")
        print(f"\nMessage:")
        print(f"   {compat['message']}")
    else:
        print(f"Message: {compat['message']}")

    print()


async def test_update_check():
    """Test update checking against PyPI."""
    print("=" * 70)
    print("TEST 3: Update Check (PyPI)")
    print("=" * 70)

    service = SelfUpgradeService()

    print("Checking for updates... (may take a few seconds)")
    update_info = await service.check_for_update()

    if update_info:
        print(f"✓ Check completed successfully")
        print(f"  Current: {update_info['current']}")
        print(f"  Latest: {update_info['latest']}")
        print(f"  Update Available: {update_info['update_available']}")
        if update_info["update_available"]:
            print(f"  Upgrade Command: {update_info['upgrade_command']}")
    else:
        print("✓ Check completed - No update info available")
        print("  (This is normal for editable installs or network issues)")

    print()


async def test_notification_display():
    """Test notification display."""
    print("=" * 70)
    print("TEST 4: Notification Display")
    print("=" * 70)

    service = SelfUpgradeService()

    # Create mock update info for display testing
    mock_update = {
        "current": "4.21.2",
        "latest": "4.21.3",
        "update_available": True,
        "upgrade_command": "pipx upgrade claude-mpm",
    }

    print("Displaying sample notification:")
    print()
    service.display_update_notification(mock_update)

    print()


def test_configuration():
    """Test configuration loading."""
    print("=" * 70)
    print("TEST 5: Configuration")
    print("=" * 70)

    config = Config()
    updates_config = config.get("updates", {})

    print("Current configuration:")
    print(f"  check_enabled: {updates_config.get('check_enabled', 'not set')}")
    print(f"  check_frequency: {updates_config.get('check_frequency', 'not set')}")
    print(f"  check_claude_code: {updates_config.get('check_claude_code', 'not set')}")
    print(f"  auto_upgrade: {updates_config.get('auto_upgrade', 'not set')}")
    print(f"  cache_ttl: {updates_config.get('cache_ttl', 'not set')}")

    print()


async def test_full_startup_check():
    """Test the full startup check (as it runs in production)."""
    print("=" * 70)
    print("TEST 6: Full Startup Check")
    print("=" * 70)

    service = SelfUpgradeService()

    print("Running full startup check...")
    print()

    result = await service.check_and_prompt_on_startup(
        auto_upgrade=False, check_claude_code=True
    )

    if result:
        print(f"\n✓ Startup check completed with update available")
    else:
        print(f"\n✓ Startup check completed - no updates needed")

    print()


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("UPDATE CHECKING SYSTEM - MANUAL TEST SUITE")
    print("=" * 70)
    print()

    try:
        # Run tests
        await test_version_detection()
        await test_claude_code_compatibility()
        await test_update_check()
        await test_notification_display()
        test_configuration()
        await test_full_startup_check()

        print("=" * 70)
        print("ALL TESTS COMPLETED")
        print("=" * 70)
        print()
        print("✓ All tests executed successfully!")
        print()
        print("Next steps:")
        print("1. Review test output above")
        print("2. Verify notifications are clear and helpful")
        print("3. Test with different configuration settings")
        print("4. Test with Claude Code installed/uninstalled")
        print()

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
