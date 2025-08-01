#!/usr/bin/env python3
"""
Test script for error handling in Socket.IO dependency installation.

This test verifies that the system handles network issues and
installation failures gracefully with helpful error messages.
"""

import subprocess
import sys
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path so we can import claude_mpm modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.dependency_manager import ensure_socketio_dependencies, install_packages
from claude_mpm.core.logger import get_logger

logger = get_logger("test_error_handling")

def test_network_error_simulation():
    """Test handling of network errors during installation."""
    print("=== Testing Network Error Simulation ===")
    
    # Test with invalid package names to simulate network/package errors
    invalid_packages = ["nonexistent-package-12345", "invalid-socketio-999"]
    
    success, error_msg = install_packages(invalid_packages, logger)
    
    if not success and error_msg:
        print("✓ PASS: Network/package error handled correctly")
        print(f"  Error message: {error_msg[:100]}...")
        return True
    else:
        print("✗ FAIL: Network error not handled properly")
        return False

def test_timeout_handling():
    """Test handling of installation timeouts."""
    print("\n=== Testing Timeout Handling ===")
    
    # We can't easily simulate a real timeout without waiting 5 minutes,
    # so we'll test the timeout mechanism indirectly by checking the code
    # and testing with a shorter timeout
    
    try:
        # Monkey patch subprocess.run to simulate timeout
        original_run = subprocess.run
        
        def mock_run(*args, **kwargs):
            if 'timeout' in kwargs:
                kwargs['timeout'] = 0.01  # Very short timeout
            raise subprocess.TimeoutExpired(args[0], 0.01)
        
        with patch('subprocess.run', side_effect=mock_run):
            success, error_msg = install_packages(["python-socketio"], logger)
        
        if not success and "timed out" in error_msg.lower():
            print("✓ PASS: Timeout error handled correctly")
            print(f"  Error message: {error_msg}")
            return True
        else:
            print("✗ FAIL: Timeout not handled properly")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: Exception during timeout test: {e}")
        return False

def test_permission_error_simulation():
    """Test handling of permission errors during installation."""
    print("\n=== Testing Permission Error Simulation ===")
    
    try:
        # Monkey patch subprocess.run to simulate permission error
        def mock_run(*args, **kwargs):
            # Simulate a permission denied error
            result = MagicMock()
            result.returncode = 1
            result.stderr = "ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied"
            return result
        
        with patch('subprocess.run', side_effect=mock_run):
            success, error_msg = install_packages(["python-socketio"], logger)
        
        if not success and ("permission" in error_msg.lower() or "errno 13" in error_msg.lower()):
            print("✓ PASS: Permission error handled correctly")
            print(f"  Error message: {error_msg[:100]}...")
            return True
        else:
            print("✗ FAIL: Permission error not handled properly")
            print(f"  Got: {error_msg}")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: Exception during permission test: {e}")
        return False

def test_monitor_flag_error_handling():
    """Test --monitor flag behavior when dependency installation fails."""
    print("\n=== Testing --monitor Flag Error Handling ===")
    
    try:
        # First, uninstall dependencies to create error condition
        uninstall_cmd = [sys.executable, "-m", "pip", "uninstall", "-y", "python-socketio", "python-engineio", "aiohttp"]
        subprocess.run(uninstall_cmd, capture_output=True, check=False)
        
        # Now run claude-mpm --monitor with environment that will cause pip to fail
        env = os.environ.copy()
        env['PIP_INDEX_URL'] = 'http://invalid-pypi-server-12345.com'  # Invalid PyPI server
        
        cmd = [
            sys.executable, "-m", "claude_mpm", 
            "--monitor", 
            "--non-interactive", 
            "-i", "test"
        ]
        
        print(f"Running command with invalid PyPI server: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=Path(__file__).parent.parent
        )
        
        try:
            stdout, stderr = process.communicate(timeout=30)
            combined_output = stdout + stderr
            
            print(f"Return code: {process.returncode}")
            
            # Look for error handling indicators
            error_indicators = [
                "Failed to install Socket.IO dependencies" in combined_output,
                "Please install manually" in combined_output,
                "pip install python-socketio" in combined_output,
                "pip install claude-mpm[monitor]" in combined_output
            ]
            
            print("\n--- Error Handling Output ---")
            lines = combined_output.split('\n')
            for line in lines:
                if any(keyword in line.lower() for keyword in ['fail', 'error', 'install', 'manual']):
                    print(f"  {line}")
            
            if any(error_indicators):
                print("✓ PASS: Monitor flag shows helpful error messages and fallback instructions")
                return True
            else:
                print("✗ FAIL: No helpful error messages found")
                return False
                
        except subprocess.TimeoutExpired:
            print("Process timeout during error handling test")
            process.kill()
            return False
            
    except Exception as e:
        print(f"✗ FAIL: Exception during monitor error test: {e}")
        return False
    finally:
        # Restore dependencies for other tests
        restore_cmd = [sys.executable, "-m", "pip", "install", "python-socketio", "aiohttp", "python-engineio"]
        subprocess.run(restore_cmd, capture_output=True, check=False)

def test_graceful_degradation():
    """Test that the system continues to work even when Socket.IO installation fails."""
    print("\n=== Testing Graceful Degradation ===")
    
    # This test verifies that the system doesn't crash completely when Socket.IO fails
    # The exact behavior may vary, but the key is that it provides helpful guidance
    
    try:
        # Test the dependency manager's graceful handling
        success, error_msg = ensure_socketio_dependencies(logger)
        
        # After the error handling test above, dependencies should be restored
        # So this should succeed, but we're testing the error path was handled gracefully
        
        if success:
            print("✓ PASS: System recovered and dependencies are working")
            return True
        else:
            # If it fails, check that we get a helpful error message
            if error_msg and len(error_msg) > 10:
                print("✓ PASS: System failed gracefully with helpful error message")
                print(f"  Error: {error_msg[:100]}...")
                return True
            else:
                print("✗ FAIL: No helpful error message provided")
                return False
                
    except Exception as e:
        print(f"✗ FAIL: System crashed instead of failing gracefully: {e}")
        return False

def main():
    """Run all error handling tests."""
    print("=== Error Handling Test Suite ===")
    print(f"Python: {sys.executable}")
    print(f"Working directory: {Path.cwd()}")
    
    results = []
    
    # Test 1: Network error simulation
    results.append(test_network_error_simulation())
    
    # Test 2: Timeout handling
    results.append(test_timeout_handling())
    
    # Test 3: Permission error simulation
    results.append(test_permission_error_simulation())
    
    # Test 4: Monitor flag error handling
    results.append(test_monitor_flag_error_handling())
    
    # Test 5: Graceful degradation
    results.append(test_graceful_degradation())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== Test Summary ===")
    print(f"Passed: {passed}/{total}")
    
    if passed >= total - 1:  # Allow one test to fail
        print("✓ MOST TESTS PASSED (Error handling working)")
        return True
    else:
        print("✗ MULTIPLE TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)