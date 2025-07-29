#!/usr/bin/env python3
"""
Comprehensive test for working directory fix.
Tests both interactive and non-interactive modes.
"""

import os
import subprocess
import sys
import tempfile
import json
from pathlib import Path


def test_non_interactive_mode():
    """Test non-interactive mode from different directory."""
    print("=== Testing Non-Interactive Mode ===")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file in the temp directory
        test_file = Path(tmpdir) / "test_file.txt"
        test_file.write_text("Test content")
        
        # Get claude-mpm path
        claude_mpm = Path(__file__).parent.parent / "claude-mpm"
        
        # Test commands that show working directory
        test_cases = [
            ("Check PWD", "pwd"),
            ("List files", "ls -la test_file.txt"),
            ("Show test file", "cat test_file.txt"),
        ]
        
        for test_name, command in test_cases:
            print(f"\n{test_name}:")
            cmd = [str(claude_mpm), "run", "-i", command, "--non-interactive"]
            
            result = subprocess.run(
                cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            
            print(f"  Command: {command}")
            print(f"  Working dir: {tmpdir}")
            
            if result.returncode == 0:
                # Extract relevant output
                output_lines = result.stdout.strip().split('\n')
                relevant_output = []
                for line in output_lines:
                    if not line.startswith('[INFO]') and not line.startswith('INFO:'):
                        relevant_output.append(line)
                
                if relevant_output:
                    print(f"  Output: {relevant_output[-1]}")
                    
                    # Check if the output is correct
                    if test_name == "Check PWD" and tmpdir in relevant_output[-1]:
                        print("  ✓ Correct working directory")
                    elif test_name == "List files" and "test_file.txt" in result.stdout:
                        print("  ✓ Can see files in working directory")
                    elif test_name == "Show test file" and "Test content" in result.stdout:
                        print("  ✓ Can read files in working directory")
                else:
                    print("  ✗ No relevant output found")
            else:
                print(f"  ✗ Command failed: {result.stderr}")


def test_interactive_mode_simulation():
    """Test that environment is set up correctly for interactive mode."""
    print("\n\n=== Testing Interactive Mode Setup ===")
    
    # Check the claude-mpm script
    claude_mpm = Path(__file__).parent.parent / "claude-mpm"
    
    print(f"Checking claude-mpm script: {claude_mpm}")
    
    # Read the script to verify environment variable handling
    with open(claude_mpm, 'r') as f:
        content = f.read()
        
    # Check for CLAUDE_MPM_USER_PWD handling
    if "CLAUDE_MPM_USER_PWD" in content:
        print("✓ CLAUDE_MPM_USER_PWD handling found in script")
    else:
        print("✗ CLAUDE_MPM_USER_PWD handling NOT found in script")
    
    # Check for working directory change
    if "os.chdir" in content or "cd " in content:
        print("✓ Working directory change logic found")
    else:
        print("✗ Working directory change logic NOT found")


def test_file_access_from_different_directory():
    """Test that Claude can access files in the user's directory."""
    print("\n\n=== Testing File Access from User Directory ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test structure
        user_project = Path(tmpdir) / "user_project"
        user_project.mkdir()
        
        (user_project / "README.md").write_text("# User Project")
        (user_project / "src").mkdir()
        (user_project / "src" / "main.py").write_text("print('Hello from user project')")
        
        # Run claude-mpm from the user project directory
        claude_mpm = Path(__file__).parent.parent / "claude-mpm"
        
        cmd = [
            str(claude_mpm),
            "run",
            "-i",
            "ls -la && echo '---' && cat README.md",
            "--non-interactive"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(user_project),
            capture_output=True,
            text=True
        )
        
        print(f"Working directory: {user_project}")
        
        if result.returncode == 0:
            if "README.md" in result.stdout and "# User Project" in result.stdout:
                print("✓ Can access files in user's working directory")
            else:
                print("✗ Cannot access files in user's working directory")
                print(f"Output: {result.stdout}")
        else:
            print(f"✗ Command failed: {result.stderr}")


def main():
    """Run all tests."""
    print("=== Comprehensive Working Directory Test ===\n")
    
    # Test 1: Non-interactive mode
    test_non_interactive_mode()
    
    # Test 2: Interactive mode setup
    test_interactive_mode_simulation()
    
    # Test 3: File access
    test_file_access_from_different_directory()
    
    print("\n\n=== Test Complete ===")
    print("\nTo fully test interactive mode:")
    print("1. cd to any directory outside claude-mpm")
    print("2. Run: /path/to/claude-mpm")
    print("3. In Claude, run: pwd")
    print("4. Verify it shows your original directory, not the claude-mpm directory")


if __name__ == "__main__":
    main()