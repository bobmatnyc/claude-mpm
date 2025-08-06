#!/usr/bin/env python3
"""
Test script for simulating fresh environment (missing Socket.IO dependencies).

This script:
1. Temporarily uninstalls Socket.IO dependencies
2. Tests the --monitor flag auto-installation
3. Restores the original state
"""

import subprocess
import sys
import os
from pathlib import Path

# Add src to path so we can import claude_mpm modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.dependency_manager import check_dependency, ensure_socketio_dependencies
from claude_mpm.core.logger import get_logger

logger = get_logger("test_fresh_env")

def get_installed_socketio_packages():
    """Get list of currently installed Socket.IO related packages."""
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "freeze"], 
                              capture_output=True, text=True, check=True)
        packages = []
        for line in result.stdout.strip().split('\n'):
            if any(pkg in line.lower() for pkg in ['socketio', 'engineio', 'aiohttp']):
                packages.append(line.split('==')[0])  # Get package name without version
        return packages
    except Exception as e:
        logger.error(f"Failed to get installed packages: {e}")
        return []

def uninstall_packages(packages):
    """Uninstall specified packages."""
    if not packages:
        return True
    
    try:
        cmd = [sys.executable, "-m", "pip", "uninstall", "-y"] + packages
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Successfully uninstalled: {packages}")
            return True
        else:
            logger.error(f"Failed to uninstall packages: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error during uninstall: {e}")
        return False

def install_packages(packages):
    """Install specified packages."""
    if not packages:
        return True
    
    try:
        cmd = [sys.executable, "-m", "pip", "install"] + packages
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Successfully installed: {packages}")
            return True
        else:
            logger.error(f"Failed to install packages: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error during install: {e}")
        return False

def test_dependency_check():
    """Test dependency checking functions."""
    print("\n=== Testing Dependency Check Functions ===")
    
    dependencies = [
        ("python-socketio", "socketio"),
        ("aiohttp", "aiohttp"), 
        ("python-engineio", "engineio")
    ]
    
    for package_name, import_name in dependencies:
        available = check_dependency(package_name, import_name)
        status = "✓ Available" if available else "✗ Missing"
        print(f"{package_name} ({import_name}): {status}")
    
    return all(check_dependency(pkg, imp) for pkg, imp in dependencies)

def test_auto_installation():
    """Test automatic installation via ensure_socketio_dependencies."""
    print("\n=== Testing Auto-Installation ===")
    
    success, error_msg = ensure_socketio_dependencies(logger)
    
    if success:
        print("✓ Auto-installation succeeded")
        return True
    else:
        print(f"✗ Auto-installation failed: {error_msg}")
        return False

def main():
    print("=== Fresh Environment Socket.IO Test ===")
    print(f"Python: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    
    # Get current packages for restoration
    original_packages = get_installed_socketio_packages()
    print(f"\nOriginal Socket.IO packages: {original_packages}")
    
    # Step 1: Check current state
    print("\n=== Step 1: Check Current State ===")
    has_deps_initially = test_dependency_check()
    print(f"Initial dependencies available: {has_deps_initially}")
    
    if not has_deps_initially:
        print("Dependencies already missing - good for fresh environment test!")
    else:
        # Step 2: Temporarily uninstall Socket.IO dependencies
        print("\n=== Step 2: Simulating Fresh Environment (Uninstalling) ===")
        socketio_packages = ["python-socketio", "python-engineio", "aiohttp"]
        
        print(f"Uninstalling packages: {socketio_packages}")
        if not uninstall_packages(socketio_packages):
            print("❌ Failed to uninstall packages for test")
            return False
        
        # Verify they're gone
        print("\nVerifying uninstallation:")
        test_dependency_check()
    
    # Step 3: Test auto-installation
    print("\n=== Step 3: Testing Auto-Installation ===")
    auto_install_success = test_auto_installation()
    
    # Step 4: Verify installation worked
    print("\n=== Step 4: Verifying Installation ===")
    has_deps_after = test_dependency_check()
    
    # Step 5: Test results
    print("\n=== Test Results ===")
    if auto_install_success and has_deps_after:
        print("✓ PASS: Auto-installation worked correctly")
        test_result = True
    else:
        print("✗ FAIL: Auto-installation did not work")
        test_result = False
    
    # Step 6: Cleanup/Restore (if we modified the environment)
    if has_deps_initially and not has_deps_after:
        print("\n=== Step 6: Restoring Original State ===")
        if original_packages:
            # Try to restore original packages
            restore_packages = [f"{pkg}" for pkg in original_packages]
            if install_packages(restore_packages):
                print("✓ Original packages restored")
            else:
                print("⚠️  Failed to restore some packages")
    
    return test_result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)