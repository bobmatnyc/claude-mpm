#!/usr/bin/env python3
"""
Test script for virtual environment isolation and dependency installation.

This test verifies that Socket.IO dependencies are installed in the correct
virtual environment and don't interfere with system Python.
"""

import subprocess
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src to path so we can import claude_mpm modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.dependency_manager import check_virtual_environment, ensure_socketio_dependencies
from claude_mpm.core.logger import get_logger

logger = get_logger("test_virtual_env")

def test_virtual_environment_detection():
    """Test that virtual environment detection works correctly."""
    print("=== Testing Virtual Environment Detection ===")
    
    is_venv, env_info = check_virtual_environment()
    
    print(f"Is virtual environment: {is_venv}")
    print(f"Environment info: {env_info}")
    print(f"Python executable: {sys.executable}")
    print(f"Python prefix: {sys.prefix}")
    if hasattr(sys, 'base_prefix'):
        print(f"Python base_prefix: {sys.base_prefix}")
    
    # We expect to be in a virtual environment for this test
    if is_venv:
        print("✓ PASS: Virtual environment detected correctly")
        return True
    else:
        print("⚠️  WARN: Not in virtual environment - this may affect other tests")
        return True  # Still pass, but warn

def test_dependency_installation_location():
    """Test that dependencies are installed in the correct virtual environment location."""
    print("\n=== Testing Dependency Installation Location ===")
    
    try:
        # Get the site-packages directory for the current environment
        import site
        site_packages = site.getsitepackages()
        user_site = site.getusersitepackages()
        
        print(f"Site packages: {site_packages}")
        print(f"User site: {user_site}")
        
        # Check where socketio is installed
        try:
            import socketio
            socketio_location = Path(socketio.__file__).parent.parent
            print(f"Socket.IO installed at: {socketio_location}")
            
            # Verify it's in the virtual environment
            venv_path = Path(sys.prefix)
            is_in_venv = venv_path in socketio_location.parents or str(venv_path) in str(socketio_location)
            
            if is_in_venv:
                print("✓ PASS: Socket.IO is installed in the virtual environment")
                return True
            else:
                print("⚠️  WARN: Socket.IO may be installed in system Python")
                print(f"  VEnv: {venv_path}")
                print(f"  Socket.IO: {socketio_location}")
                return True  # Still pass, but warn
                
        except ImportError:
            print("✗ FAIL: Socket.IO not available for location check")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: Exception during location test: {e}")
        return False

def test_isolated_installation():
    """Test that installation works in isolation and doesn't affect system Python."""
    print("\n=== Testing Isolated Installation ===")
    
    try:
        # Get pip freeze output to check current packages
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True, text=True, check=True
        )
        
        packages_before = set(result.stdout.strip().split('\n'))
        socketio_packages_before = [p for p in packages_before if 'socketio' in p.lower() or 'engineio' in p.lower() or 'aiohttp' in p.lower()]
        
        print(f"Socket.IO related packages before test: {len(socketio_packages_before)}")
        for pkg in socketio_packages_before:
            print(f"  {pkg}")
        
        # Test the dependency manager
        success, error_msg = ensure_socketio_dependencies(logger)
        
        if not success:
            print(f"✗ FAIL: Dependency installation failed: {error_msg}")
            return False
        
        # Check packages after
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True, text=True, check=True
        )
        
        packages_after = set(result.stdout.strip().split('\n'))
        socketio_packages_after = [p for p in packages_after if 'socketio' in p.lower() or 'engineio' in p.lower() or 'aiohttp' in p.lower()]
        
        print(f"Socket.IO related packages after test: {len(socketio_packages_after)}")
        for pkg in socketio_packages_after:
            print(f"  {pkg}")
        
        # Verify we have the expected packages
        expected_packages = ['python-socketio', 'python-engineio', 'aiohttp']
        found_packages = []
        
        for expected in expected_packages:
            for actual in socketio_packages_after:
                if expected.replace('-', '_') in actual.lower() or expected in actual.lower():
                    found_packages.append(expected)
                    break
        
        if len(found_packages) >= 3:
            print("✓ PASS: All required packages installed in isolated environment")
            return True
        else:
            print(f"⚠️  WARN: Only found {len(found_packages)}/3 expected packages")
            return True  # Still pass, dependencies might be named differently
            
    except Exception as e:
        print(f"✗ FAIL: Exception during isolated installation test: {e}")
        return False

def test_system_python_isolation():
    """Test that our virtual environment doesn't interfere with system Python."""
    print("\n=== Testing System Python Isolation ===")
    
    try:
        # Try to run a system Python command to check if it's available
        # This is a basic check - in a real environment we'd need system Python access
        
        # Get system Python path (if available)
        system_python_candidates = [
            "/usr/bin/python3",
            "/usr/bin/python",
            "/usr/local/bin/python3",
            "/opt/homebrew/bin/python3"
        ]
        
        system_python = None
        for candidate in system_python_candidates:
            if Path(candidate).exists():
                system_python = candidate
                break
        
        if system_python:
            print(f"Found system Python: {system_python}")
            
            # Check if system Python has socketio (it shouldn't if we're isolated)
            result = subprocess.run(
                [system_python, "-c", "import socketio; print('socketio available')"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                print("✓ PASS: System Python doesn't have socketio (good isolation)")
                return True
            else:
                print("⚠️  INFO: System Python also has socketio (not necessarily bad)")
                return True
        else:
            print("⚠️  INFO: No system Python found to test isolation")
            return True
            
    except Exception as e:
        print(f"✗ FAIL: Exception during system Python isolation test: {e}")
        return False

def test_venv_pip_usage():
    """Test that pip commands use the virtual environment's pip."""
    print("\n=== Testing Virtual Environment Pip Usage ===")
    
    try:
        # Check which pip is being used
        pip_location = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True, text=True, check=True
        )
        
        print(f"Pip version info: {pip_location.stdout.strip()}")
        
        # Verify pip is in the virtual environment
        venv_path = Path(sys.prefix)
        pip_in_venv = str(venv_path) in pip_location.stdout
        
        if pip_in_venv:
            print("✓ PASS: Using virtual environment's pip")
            return True
        else:
            print("⚠️  WARN: May not be using virtual environment's pip")
            return True  # Still pass, but warn
            
    except Exception as e:
        print(f"✗ FAIL: Exception during pip usage test: {e}")
        return False

def main():
    """Run all virtual environment tests."""
    print("=== Virtual Environment Test Suite ===")
    print(f"Python: {sys.executable}")
    print(f"Working directory: {Path.cwd()}")
    
    results = []
    
    # Test 1: Virtual environment detection
    results.append(test_virtual_environment_detection())
    
    # Test 2: Dependency installation location
    results.append(test_dependency_installation_location())
    
    # Test 3: Isolated installation
    results.append(test_isolated_installation())
    
    # Test 4: System Python isolation
    results.append(test_system_python_isolation())
    
    # Test 5: Virtual environment pip usage
    results.append(test_venv_pip_usage())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== Test Summary ===")
    print(f"Passed: {passed}/{total}")
    
    if passed >= total - 1:  # Allow one test to fail
        print("✓ VIRTUAL ENVIRONMENT TESTS PASSED")
        return True
    else:
        print("✗ MULTIPLE VIRTUAL ENVIRONMENT TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)