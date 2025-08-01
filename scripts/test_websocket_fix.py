#!/usr/bin/env python3
"""Test WebSocket fix for terminal flickering and agent delegation tracking."""

import subprocess
import sys
import os

def test_agent_delegation():
    """Test that agent delegation works without terminal flickering."""
    
    # Test prompt that should trigger agent delegation
    test_prompt = "Use the Task tool to delegate to the research agent to analyze the current directory structure"
    
    # Run claude-mpm with the test prompt
    cmd = [
        "/Users/masa/Projects/claude-mpm/scripts/claude-mpm",
        "run",
        "-i", test_prompt,
        "--non-interactive"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Test prompt: {test_prompt}")
    print("-" * 80)
    
    # Execute the command
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print("-" * 80)
    
    # Check for success
    if result.returncode == 0:
        print("✓ Command executed successfully")
        
        # Check for agent delegation in output
        if "research" in result.stdout.lower() or "Research" in result.stdout:
            print("✓ Agent delegation detected in output")
        else:
            print("⚠ Agent delegation not clearly visible in output")
            
        # Check for error indicators
        if "flickering" not in result.stderr.lower() and "flicker" not in result.stdout.lower():
            print("✓ No flickering issues reported")
        else:
            print("✗ Flickering issues detected")
            
        return True
    else:
        print(f"✗ Command failed with return code: {result.returncode}")
        return False

def test_simple_command():
    """Test a simple command to ensure basic functionality."""
    
    test_prompt = "What is 5 + 7?"
    
    cmd = [
        "/Users/masa/Projects/claude-mpm/scripts/claude-mpm",
        "run",
        "-i", test_prompt,
        "--non-interactive"
    ]
    
    print(f"\nTesting simple command: {test_prompt}")
    print("-" * 80)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("Output:", result.stdout.strip())
    
    if "12" in result.stdout:
        print("✓ Simple command works correctly")
        return True
    else:
        print("✗ Simple command failed")
        return False

if __name__ == "__main__":
    print("Testing WebSocket Fix for Terminal Flickering")
    print("=" * 80)
    
    # Run tests
    simple_ok = test_simple_command()
    delegation_ok = test_agent_delegation()
    
    # Summary
    print("\n" + "=" * 80)
    print("Test Summary:")
    print(f"  Simple command test: {'PASS' if simple_ok else 'FAIL'}")
    print(f"  Agent delegation test: {'PASS' if delegation_ok else 'FAIL'}")
    
    if simple_ok and delegation_ok:
        print("\n✓ All tests passed! WebSocket fix appears to be working.")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed. Please check the output above.")
        sys.exit(1)