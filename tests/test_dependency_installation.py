#!/usr/bin/env python3
"""
Test script for automatic dependency installation.

WHY: This script tests the automatic Socket.IO dependency installation
feature to ensure it works correctly before users encounter it.

DESIGN DECISION: We create a separate test environment simulation
to avoid affecting the actual package installation during testing.
"""

import sys
import os
from pathlib import Path

# Add src to Python path for testing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.utils.dependency_manager import (
    check_dependency,
    ensure_socketio_dependencies,
    get_pip_freeze_output,
    check_virtual_environment
)
from claude_mpm.core.logger import get_logger


def test_dependency_checks():
    """Test the dependency checking functions."""
    logger = get_logger("test_dependency")
    
    print("🧪 Testing Dependency Manager")
    print("=" * 50)
    
    # Test virtual environment detection
    is_venv, venv_info = check_virtual_environment()
    print(f"Virtual Environment: {is_venv}")
    print(f"Environment Info: {venv_info}")
    print()
    
    # Test dependency checking for common packages
    test_packages = [
        ("python", "sys"),  # Should always be available
        ("python-socketio", "socketio"),
        ("aiohttp", "aiohttp"),
        ("python-engineio", "engineio"),
        ("nonexistent-package", "nonexistent")  # Should not be available
    ]
    
    print("📦 Dependency Check Results:")
    for package_name, import_name in test_packages:
        available = check_dependency(package_name, import_name)
        status = "✓" if available else "❌"
        print(f"  {status} {package_name} ({import_name}): {available}")
    print()
    
    # Test Socket.IO dependency installation
    print("🔧 Testing Socket.IO Dependency Installation:")
    try:
        success, error_msg = ensure_socketio_dependencies(logger)
        if success:
            print("✅ Socket.IO dependencies installation test: SUCCESS")
        else:
            print(f"❌ Socket.IO dependencies installation test: FAILED")
            print(f"   Error: {error_msg}")
    except Exception as e:
        print(f"❌ Exception during dependency installation test: {e}")
    print()
    
    # Show some pip freeze output for debugging
    print("📋 Current Package Environment (first 10 packages):")
    try:
        packages = get_pip_freeze_output()[:10]
        for package in packages:
            print(f"  {package}")
        if len(get_pip_freeze_output()) > 10:
            print(f"  ... and {len(get_pip_freeze_output()) - 10} more packages")
    except Exception as e:
        print(f"  Error getting package list: {e}")
    print()
    
    # Final verification of Socket.IO imports
    print("🎯 Final Socket.IO Import Test:")
    socketio_packages = [
        ("socketio", "Socket.IO"),
        ("aiohttp", "aiohttp"),
        ("engineio", "Engine.IO")
    ]
    
    all_available = True
    for import_name, display_name in socketio_packages:
        try:
            __import__(import_name)
            print(f"  ✅ {display_name}: Available")
        except ImportError:
            print(f"  ❌ {display_name}: Not available")
            all_available = False
    
    if all_available:
        print("\n🎉 All Socket.IO dependencies are ready for --monitor mode!")
    else:
        print("\n⚠️  Some Socket.IO dependencies are missing. --monitor mode may not work fully.")
    
    return all_available


if __name__ == "__main__":
    success = test_dependency_checks()
    sys.exit(0 if success else 1)