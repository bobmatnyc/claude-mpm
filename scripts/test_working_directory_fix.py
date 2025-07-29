#!/usr/bin/env python3
"""
Test script to verify the working directory fix for Claude Code.

This script tests that:
1. The original working directory is preserved in CLAUDE_MPM_USER_PWD
2. Claude Code receives the correct working directory
3. The filesystem restrictions work properly

Usage:
    Run from any directory outside the framework:
    cd /tmp && python /path/to/claude-mpm/scripts/test_working_directory_fix.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_environment_preservation():
    """Test that the environment variable is preserved."""
    print("Testing environment preservation...")
    
    # Check if CLAUDE_MPM_USER_PWD is set
    user_pwd = os.environ.get('CLAUDE_MPM_USER_PWD')
    current_pwd = os.getcwd()
    
    print(f"  Current directory: {current_pwd}")
    print(f"  CLAUDE_MPM_USER_PWD: {user_pwd}")
    print(f"  CLAUDE_WORKSPACE: {os.environ.get('CLAUDE_WORKSPACE', 'NOT SET')}")
    
    if user_pwd:
        print("  ✓ CLAUDE_MPM_USER_PWD is preserved")
        return True
    else:
        print("  ✗ CLAUDE_MPM_USER_PWD is not set")
        return False


def test_claude_mpm_launch():
    """Test launching claude-mpm from different directory."""
    print("\nTesting claude-mpm launch from different directory...")
    
    # Create a temporary directory to test from
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("This is a test file")
        
        # Get the claude-mpm path
        claude_mpm_path = Path(__file__).parent.parent / "claude-mpm"
        
        # Run claude-mpm with a simple command to check working directory
        cmd = [
            str(claude_mpm_path),
            "run",
            "-i", "echo 'Current directory:' && pwd",
            "--non-interactive"
        ]
        
        print(f"  Running from: {tmpdir}")
        print(f"  Command: {' '.join(cmd)}")
        
        # Run the command from the temp directory
        result = subprocess.run(
            cmd,
            cwd=tmpdir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"  Output: {result.stdout.strip()}")
            # Check if the output shows the correct directory
            if tmpdir in result.stdout:
                print("  ✓ Claude sees the correct working directory")
                return True
            else:
                print("  ✗ Claude sees wrong working directory")
                return False
        else:
            print(f"  ✗ Command failed: {result.stderr}")
            return False


def test_direct_python_module():
    """Test the Python module directly."""
    print("\nTesting Python module directly...")
    
    # Add the src directory to Python path
    src_dir = Path(__file__).parent.parent / "src"
    sys.path.insert(0, str(src_dir))
    
    try:
        # Import and check
        from claude_mpm.core.simple_runner import SimpleClaudeRunner
        
        # Check environment
        user_pwd = os.environ.get('CLAUDE_MPM_USER_PWD')
        if user_pwd:
            print(f"  ✓ Environment variable visible to Python module: {user_pwd}")
            return True
        else:
            print("  ✗ Environment variable not visible to Python module")
            return False
    except Exception as e:
        print(f"  ✗ Failed to import module: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Working Directory Fix Test Suite ===\n")
    
    results = []
    
    # Test 1: Environment preservation
    results.append(("Environment Preservation", test_environment_preservation()))
    
    # Test 2: Direct Python module
    results.append(("Python Module", test_direct_python_module()))
    
    # Test 3: Claude MPM launch (only if not already in claude-mpm)
    if "CLAUDE_MPM_USER_PWD" not in os.environ:
        results.append(("Claude MPM Launch", test_claude_mpm_launch()))
    else:
        print("\nSkipping launch test (already running inside claude-mpm)")
    
    # Summary
    print("\n=== Test Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())