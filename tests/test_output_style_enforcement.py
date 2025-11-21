#!/usr/bin/env python3
"""Test script to verify output style enforcement mechanism.

This script tests:
1. Initial deployment and activation of claude-mpm style
2. Detection when user changes the style
3. Automatic re-enforcement of claude-mpm style
4. Logging and user notifications
"""

import json
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.output_style_manager import OutputStyleManager


def test_initial_deployment():
    """Test initial deployment and activation."""
    print("=" * 60)
    print("TEST 1: Initial Deployment and Activation")
    print("=" * 60)

    # Create manager
    manager = OutputStyleManager()

    # Check version detection
    print(f"Claude version: {manager.claude_version or 'Not detected'}")
    print(f"Supports output styles: {manager.supports_output_styles()}")

    if manager.supports_output_styles():
        # Deploy style
        content = manager.extract_output_style_content()
        deployed = manager.deploy_output_style(content)
        print(f"Deployment successful: {deployed}")

        # Check settings
        if manager.settings_file.exists():
            settings = json.loads(manager.settings_file.read_text())
            print(
                f"Active style in settings: {settings.get('activeOutputStyle', 'none')}"
            )

        # Log enforcement status
        manager.log_enforcement_status()
    else:
        print("Claude version does not support output styles")

    print()


def test_style_change_detection():
    """Test detection when user changes the style."""
    print("=" * 60)
    print("TEST 2: Style Change Detection and Re-enforcement")
    print("=" * 60)

    manager = OutputStyleManager()

    if not manager.supports_output_styles():
        print("Skipping - Claude version does not support output styles")
        return

    # Ensure claude-mpm is deployed
    content = manager.extract_output_style_content()
    manager.deploy_output_style(content)

    # Simulate user changing the style
    print("\nSimulating user changing style to 'default'...")
    if manager.settings_file.exists():
        settings = json.loads(manager.settings_file.read_text())
        settings["activeOutputStyle"] = "default"
        manager.settings_file.write_text(json.dumps(settings, indent=2))
        print("Changed activeOutputStyle to 'default'")

    # Check current status
    settings = json.loads(manager.settings_file.read_text())
    print(f"Current style after change: {settings.get('activeOutputStyle')}")

    # Perform enforcement check
    print("\nPerforming enforcement check...")
    enforced = manager.enforce_style_periodically(force_check=True)
    print(f"Enforcement successful: {enforced}")

    # Check status after enforcement
    settings = json.loads(manager.settings_file.read_text())
    print(f"Style after enforcement: {settings.get('activeOutputStyle')}")

    # Log final status
    manager.log_enforcement_status()

    print()


def test_multiple_enforcements():
    """Test multiple enforcement cycles."""
    print("=" * 60)
    print("TEST 3: Multiple Enforcement Cycles")
    print("=" * 60)

    manager = OutputStyleManager()

    if not manager.supports_output_styles():
        print("Skipping - Claude version does not support output styles")
        return

    # Deploy initially
    content = manager.extract_output_style_content()
    manager.deploy_output_style(content)

    # Simulate multiple user changes
    for i in range(3):
        print(f"\n--- Cycle {i + 1} ---")

        # Change style
        alternative_styles = ["default", "minimal", "verbose"]
        new_style = alternative_styles[i % len(alternative_styles)]

        if manager.settings_file.exists():
            settings = json.loads(manager.settings_file.read_text())
            settings["activeOutputStyle"] = new_style
            manager.settings_file.write_text(json.dumps(settings, indent=2))
            print(f"Changed style to: {new_style}")

        # Wait to ensure different timestamp
        time.sleep(0.1)

        # Enforce (with force_check to bypass time limit)
        manager.enforce_style_periodically(force_check=True)

        # Check result
        settings = json.loads(manager.settings_file.read_text())
        print(f"Style after enforcement: {settings.get('activeOutputStyle')}")
        print(f"Enforcement count: {manager._enforcement_count}")

    # Final status
    print("\n--- Final Status ---")
    manager.log_enforcement_status()

    print()


def test_enforcement_with_missing_settings():
    """Test enforcement when settings.json doesn't exist."""
    print("=" * 60)
    print("TEST 4: Enforcement with Missing Settings")
    print("=" * 60)

    # Create a temporary directory for testing
    with tmp_path as tmpdir:
        test_dir = Path(tmpdir) / ".claude"
        test_dir.mkdir(parents=True)

        # Create manager with mocked paths
        manager = OutputStyleManager()
        manager.settings_file = test_dir / "settings.json"
        manager.output_style_dir = test_dir / "output-styles"

        if not manager.supports_output_styles():
            print("Skipping - Claude version does not support output styles")
            return

        print(f"Settings file exists: {manager.settings_file.exists()}")

        # Deploy style (should create settings)
        content = manager.extract_output_style_content()
        deployed = manager.deploy_output_style(content)
        print(f"Deployment successful: {deployed}")

        # Check if settings was created
        print(f"Settings file created: {manager.settings_file.exists()}")

        if manager.settings_file.exists():
            settings = json.loads(manager.settings_file.read_text())
            print(f"Active style: {settings.get('activeOutputStyle')}")

        # Log status
        manager.log_enforcement_status()

    print()


def test_enforcement_status_display():
    """Test the enforcement status display in different scenarios."""
    print("=" * 60)
    print("TEST 5: Enforcement Status Display")
    print("=" * 60)

    manager = OutputStyleManager()

    # Test status display for different scenarios
    print("Scenario 1: Fresh start")
    manager._enforcement_count = 0
    manager.log_enforcement_status()

    print("\nScenario 2: After one enforcement")
    manager._enforcement_count = 1
    manager.log_enforcement_status()

    print("\nScenario 3: After multiple enforcements")
    manager._enforcement_count = 5
    manager.log_enforcement_status()

    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("OUTPUT STYLE ENFORCEMENT TEST SUITE")
    print("=" * 60 + "\n")

    # Run tests
    test_initial_deployment()
    test_style_change_detection()
    test_multiple_enforcements()
    test_enforcement_with_missing_settings()
    test_enforcement_status_display()

    print("=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
