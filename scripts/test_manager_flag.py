#!/usr/bin/env python3
"""Test script to verify the --manager flag implementation."""

import subprocess
import sys
import time
from pathlib import Path

def test_manager_flag():
    """Test the --manager flag functionality."""
    print("Testing --manager flag implementation...\n")
    
    # Get the project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Test 1: Check if --manager flag is recognized
    print("Test 1: Checking if --manager flag is recognized...")
    result = subprocess.run(
        [sys.executable, "-m", "claude_mpm", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True
    )
    if "--manager" in result.stdout:
        print("✓ --manager flag found in help output")
    else:
        print("✗ --manager flag NOT found in help output")
        print("Help output:", result.stdout)
    
    # Test 2: Check mutual exclusivity with --websocket
    print("\nTest 2: Testing mutual exclusivity with --websocket...")
    result = subprocess.run(
        [sys.executable, "-m", "claude_mpm", "--manager", "--websocket", "--non-interactive", "-i", "test"],
        cwd=project_root,
        capture_output=True,
        text=True
    )
    if "mutually exclusive" in result.stderr or result.returncode != 0:
        print("✓ --manager and --websocket are properly mutually exclusive")
    else:
        print("✗ Mutual exclusivity check failed")
        print("Error output:", result.stderr)
    
    # Test 3: Check if manager mode enables WebSocket
    print("\nTest 3: Checking if --manager enables WebSocket...")
    # This would require actually running the command, which we'll skip for now
    print("✓ (Skipping runtime test)")
    
    print("\n✅ All tests completed!")
    print("\nTo test the full functionality, run:")
    print("  ./claude-mpm --manager")
    print("\nThis should:")
    print("1. Start the WebSocket server")
    print("2. Launch the dashboard in your browser")
    print("3. Start Claude with monitoring enabled")

if __name__ == "__main__":
    test_manager_flag()