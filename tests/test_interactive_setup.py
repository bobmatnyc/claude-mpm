#!/usr/bin/env python3
"""Test interactive mode setup"""

import subprocess
import os
from pathlib import Path


def test_interactive_setup():
    """Test that interactive mode would get correct directory."""
    
    # Simulate what happens when claude-mpm is run
    print("=== Testing Interactive Mode Setup ===\n")
    
    # Get paths
    claude_mpm_dir = Path(__file__).parent.parent
    scripts_dir = claude_mpm_dir / "scripts"
    
    # Show what the script does
    print("1. When you run claude-mpm from any directory:")
    print(f"   - Your current directory is preserved in CLAUDE_MPM_USER_PWD")
    print(f"   - The script changes to: {claude_mpm_dir}")
    print(f"   - But then the Python code changes back to your original directory")
    
    # Test environment variable
    print("\n2. Testing environment variable preservation:")
    
    # Set a test directory
    test_pwd = "/tmp/myproject"
    env = os.environ.copy()
    env['CLAUDE_MPM_USER_PWD'] = test_pwd
    
    # Run a simple test
    result = subprocess.run(
        [str(claude_mpm_dir / "claude-mpm"), "run", "-i", "echo $CLAUDE_MPM_USER_PWD", "--non-interactive"],
        capture_output=True,
        text=True,
        env=env
    )
    
    if test_pwd in result.stdout:
        print(f"   ✓ Environment variable preserved: {test_pwd}")
    else:
        print("   ✗ Environment variable not preserved")
    
    print("\n3. Interactive mode behavior:")
    print("   When claude-mpm launches Claude in interactive mode:")
    print("   - It sets CLAUDE_WORKSPACE to your original directory")
    print("   - It changes the working directory to your original directory")
    print("   - Claude Code sees your directory, not the framework directory")
    
    print("\n=== How to Test Interactive Mode ===")
    print("1. Open a new terminal")
    print("2. cd /tmp  (or any directory outside claude-mpm)")
    print("3. Run: " + str(claude_mpm_dir / "claude-mpm"))
    print("4. In Claude, type: pwd")
    print("5. It should show /tmp, not " + str(claude_mpm_dir))


if __name__ == "__main__":
    test_interactive_setup()