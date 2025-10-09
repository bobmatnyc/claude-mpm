#!/usr/bin/env python3
"""
Test script to demonstrate PEP 668 fix.

This script tests the proper environment detection and flag selection.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.robust_installer import InstallStrategy, RobustPackageInstaller


def test_environment_detection():
    """Test environment detection."""
    installer = RobustPackageInstaller()

    print("=" * 60)
    print("ENVIRONMENT DETECTION TEST")
    print("=" * 60)
    print(f"Python: {sys.executable}")
    print(
        f"Version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    print()

    print(f"In virtualenv: {installer.in_virtualenv}")
    print(f"PEP 668 managed: {installer.is_pep668_managed}")
    print()

    # Test command building
    cmd = installer._build_install_command("test-package", InstallStrategy.PIP)
    print("Generated pip command:")
    print(f"  {' '.join(cmd)}")
    print()

    # Analyze flags
    has_break_system = "--break-system-packages" in cmd
    has_user = "--user" in cmd

    print("Flags analysis:")
    print(f"  --break-system-packages: {has_break_system}")
    print(f"  --user: {has_user}")
    print()

    # Verify correctness
    print("Verification:")
    if installer.in_virtualenv:
        if not has_break_system and not has_user:
            print("  ✓ CORRECT: No special flags in virtualenv")
        else:
            print("  ✗ ERROR: Should not use special flags in virtualenv!")
    elif installer.is_pep668_managed:
        if has_break_system and not has_user:
            print("  ✓ CORRECT: Using --break-system-packages only")
        else:
            print("  ✗ ERROR: Should use --break-system-packages only!")
    elif has_user and not has_break_system:
        print("  ✓ CORRECT: Using --user for system Python")
    else:
        print("  ✗ ERROR: Should use --user for system Python!")

    print("=" * 60)


if __name__ == "__main__":
    test_environment_detection()
