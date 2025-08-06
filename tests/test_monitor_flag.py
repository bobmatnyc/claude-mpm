#!/usr/bin/env python3
"""
Test script for --monitor flag functionality.
"""

import subprocess
import sys
import time
import signal
from pathlib import Path

def test_monitor_flag_basic():
    """Test basic --monitor flag functionality."""
    print("=== Testing --monitor Flag (Basic) ===")
    
    try:
        # Run claude-mpm with --monitor flag in non-interactive mode
        cmd = [
            sys.executable, "-m", "claude_mpm", 
            "--monitor", 
            "--non-interactive", 
            "-i", "test command"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        # Give it a few seconds to start up
        try:
            stdout, stderr = process.communicate(timeout=15)
            
            print("\n--- STDOUT ---")
            print(stdout)
            print("\n--- STDERR ---")
            print(stderr)
            
            return_code = process.returncode
            print(f"\nReturn code: {return_code}")
            
            # Analyze the output
            success_indicators = [
                "Socket.IO dependencies ready" in stdout,
                "Socket.IO server enabled" in stdout,
                "checking Socket.IO dependencies" in stdout.lower() or "checking Socket.IO dependencies" in stderr.lower()
            ]
            
            if any(success_indicators):
                print("✓ PASS: Monitor flag shows dependency checking/installation")
                return True
            else:
                print("✗ FAIL: No dependency checking indicators found")
                return False
                
        except subprocess.TimeoutExpired:
            print("Process timeout - killing process")
            process.kill()
            stdout, stderr = process.communicate()
            print(f"Partial output: {stdout[:500]}...")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: Exception during test: {e}")
        return False

def test_monitor_flag_help():
    """Test that --monitor flag is properly documented."""
    print("\n=== Testing --monitor Flag Documentation ===")
    
    try:
        cmd = [sys.executable, "-m", "claude_mpm", "--help"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if "--monitor" in result.stdout:
            print("✓ PASS: --monitor flag is documented in help")
            return True
        else:
            print("✗ FAIL: --monitor flag not found in help")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: Exception during help test: {e}")
        return False

def main():
    """Run all monitor flag tests."""
    print("=== Monitor Flag Test Suite ===")
    
    results = []
    
    # Test 1: Help documentation
    results.append(test_monitor_flag_help())
    
    # Test 2: Basic functionality
    results.append(test_monitor_flag_basic())
    
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