#!/usr/bin/env python3
"""
Test script to verify the enhanced release.py functionality.

This script tests the improved npm version synchronization and error handling
without actually performing a release.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.release import ReleaseManager


def test_version_sync():
    """Test version synchronization check."""
    print("Testing version synchronization check...")
    
    manager = ReleaseManager(dry_run=True)
    result = manager.check_version_sync()
    
    print(f"Version sync check result: {result}")
    print()


def test_npm_validation():
    """Test npm package validation."""
    print("Testing npm package validation...")
    
    manager = ReleaseManager(dry_run=True)
    result = manager.validate_npm_package()
    
    print(f"NPM validation result: {result}")
    print()


def test_package_json_update():
    """Test package.json update with edge cases."""
    print("Testing package.json update...")
    
    manager = ReleaseManager(dry_run=True)
    
    # Test with current version
    current_version = manager.get_current_version()
    print(f"Current version: {current_version}")
    
    # Test version validation
    test_versions = [
        ("2.1.0", True),    # Valid version
        ("2.1.0.beta", False),  # Invalid format
        ("invalid", False),  # Invalid format
        (current_version, True),  # Same version (should handle gracefully)
    ]
    
    for version, expected_valid in test_versions:
        print(f"\nTesting version: {version}")
        try:
            result = manager.update_package_json(version)
            print(f"  Result: {'Success' if result else 'Failed'}")
            if expected_valid and not result:
                print(f"  WARNING: Expected success for {version}")
            elif not expected_valid and result:
                print(f"  WARNING: Expected failure for {version}")
        except Exception as e:
            print(f"  Exception: {e}")
    
    print()


def check_npm_setup():
    """Check if npm is properly set up."""
    print("Checking npm setup...")
    
    manager = ReleaseManager(dry_run=True)
    
    # Check npm installation
    npm_check = manager.run_command(["which", "npm"], check=False)
    if npm_check.returncode == 0:
        print("✓ npm is installed")
        
        # Check npm version
        version_result = manager.run_command(["npm", "--version"], check=False)
        if version_result.returncode == 0:
            print(f"  npm version: {version_result.stdout.strip()}")
    else:
        print("✗ npm is not installed")
    
    # Check if logged in
    whoami_result = manager.run_command(["npm", "whoami"], check=False)
    if whoami_result.returncode == 0:
        print(f"✓ Logged in to npm as: {whoami_result.stdout.strip()}")
    else:
        print("✗ Not logged in to npm")
    
    # Check package.json
    package_json_path = project_root / "package.json"
    if package_json_path.exists():
        print("✓ package.json exists")
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
            print(f"  Package name: {package_data.get('name')}")
            print(f"  Package version: {package_data.get('version')}")
    else:
        print("✗ package.json not found")
    
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Release Script Enhancements")
    print("=" * 60)
    print()
    
    check_npm_setup()
    test_version_sync()
    test_npm_validation()
    test_package_json_update()
    
    print("=" * 60)
    print("Tests completed!")
    print("\nNote: This is a dry-run test. No actual changes were made.")
    print("The enhanced release.py script includes:")
    print("- Robust error handling for package.json updates")
    print("- Version format validation")
    print("- npm package validation before publishing")
    print("- Improved npm error detection and reporting")
    print("- Better version synchronization checking")
    print("- Progressive retry for npm registry verification")
    print("=" * 60)


if __name__ == "__main__":
    main()