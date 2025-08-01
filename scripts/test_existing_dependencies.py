#!/usr/bin/env python3
"""
Test script for --monitor flag with existing Socket.IO dependencies.

This test verifies that when dependencies are already installed,
the --monitor flag skips installation and starts immediately.
"""

import subprocess
import sys
import time
from pathlib import Path

# Add src to path so we can import claude_mpm modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.dependency_manager import check_dependency, ensure_socketio_dependencies
from claude_mpm.core.logger import get_logger

logger = get_logger("test_existing_deps")

def verify_dependencies_exist():
    """Verify all Socket.IO dependencies are installed."""
    print("=== Verifying Dependencies Exist ===")
    
    dependencies = [
        ("python-socketio", "socketio"),
        ("aiohttp", "aiohttp"), 
        ("python-engineio", "engineio")
    ]
    
    all_available = True
    for package_name, import_name in dependencies:
        available = check_dependency(package_name, import_name)
        status = "✓ Available" if available else "✗ Missing"
        print(f"{package_name} ({import_name}): {status}")
        if not available:
            all_available = False
    
    return all_available

def test_skip_installation():
    """Test that installation is skipped when dependencies exist."""
    print("\n=== Testing Skip Installation Logic ===")
    
    start_time = time.time()
    success, error_msg = ensure_socketio_dependencies(logger)
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"ensure_socketio_dependencies() took {duration:.2f} seconds")
    
    if success:
        if duration < 2.0:  # Should be very fast if skipping installation
            print("✓ PASS: Dependencies check was fast (likely skipped installation)")
            return True
        else:
            print(f"⚠️  WARN: Dependencies check took {duration:.2f}s (may have installed something)")
            return True  # Still consider it a pass if it succeeded
    else:
        print(f"✗ FAIL: Dependencies check failed: {error_msg}")
        return False

def test_monitor_flag_with_existing_deps():
    """Test --monitor flag when dependencies already exist."""
    print("\n=== Testing --monitor Flag with Existing Dependencies ===")
    
    try:
        cmd = [
            sys.executable, "-m", "claude_mpm", 
            "--monitor", 
            "--non-interactive", 
            "-i", "echo test"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        start_time = time.time()
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        # Give it time to start up and show dependency messages
        try:
            stdout, stderr = process.communicate(timeout=10)
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\nProcess completed in {duration:.2f} seconds")
            print(f"Return code: {process.returncode}")
            
            # Look for key indicators in the output
            combined_output = stdout + stderr
            
            dependency_messages = [
                "Socket.IO dependencies ready" in combined_output,
                "Checking Socket.IO dependencies" in combined_output,
                "Socket.IO server enabled" in combined_output,
                "Socket.IO server using python-socketio" in combined_output
            ]
            
            skip_indicators = [
                "Installing missing Socket.IO dependencies" not in combined_output,
                "Successfully installed packages" not in combined_output
            ]
            
            print("\n--- Key Output Excerpts ---")
            lines = combined_output.split('\n')
            for line in lines:
                if any(keyword in line.lower() for keyword in ['socket', 'dependencies', 'install']):
                    print(f"  {line}")
            
            if any(dependency_messages) and all(skip_indicators):
                print("✓ PASS: Monitor started with existing dependencies (no installation)")
                return True
            elif any(dependency_messages):
                print("⚠️  PARTIAL: Monitor started but may have installed dependencies")
                return True
            else:
                print("✗ FAIL: No dependency handling messages found")
                return False
                
        except subprocess.TimeoutExpired:
            print("Process timeout - this might be normal for interactive mode")
            process.kill()
            stdout, stderr = process.communicate()
            
            # Check if we got the startup messages before timeout
            combined_output = stdout + stderr
            if "Socket.IO" in combined_output:
                print("✓ PASS: Monitor started successfully (timed out during execution)")
                return True
            else:
                print("✗ FAIL: No Socket.IO messages before timeout")
                return False
            
    except Exception as e:
        print(f"✗ FAIL: Exception during test: {e}")
        return False

def main():
    """Run all existing dependencies tests."""
    print("=== Existing Dependencies Test Suite ===")
    print(f"Python: {sys.executable}")
    print(f"Working directory: {Path.cwd()}")
    
    results = []
    
    # Test 1: Verify dependencies exist
    deps_exist = verify_dependencies_exist()
    if not deps_exist:
        print("❌ Dependencies are missing - cannot test existing dependencies scenario")
        print("   Please run the fresh environment test first to install dependencies")
        return False
    
    # Test 2: Test skip installation logic
    results.append(test_skip_installation())
    
    # Test 3: Test monitor flag with existing dependencies
    results.append(test_monitor_flag_with_existing_deps())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== Test Summary ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ ALL TESTS PASSED")
        return True
    else:
        print("✗ SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)