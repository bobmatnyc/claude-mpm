#!/usr/bin/env python3
"""
Test script for memory CLI commands.

WHY: This script tests the memory CLI commands to ensure they work correctly
before full integration testing.
"""

import subprocess
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def run_command(cmd):
    """Run a command and return the output."""
    print(f"\n🔧 Running: {cmd}")
    print("-" * 80)
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}", file=sys.stderr)
    
    return result.returncode


def main():
    """Test memory CLI commands."""
    print("Testing Memory CLI Commands")
    print("=" * 80)
    
    # Test status command
    print("\n1. Testing memory status command:")
    run_command("python -m claude_mpm.cli memory status")
    
    # Test view command without agent_id (should fail)
    print("\n2. Testing memory view command without agent_id (should show help):")
    run_command("python -m claude_mpm.cli memory view")
    
    # Test view command with agent_id
    print("\n3. Testing memory view command with agent_id:")
    run_command("python -m claude_mpm.cli memory view test-agent")
    
    # Test add command
    print("\n4. Testing memory add command:")
    run_command('python -m claude_mpm.cli memory add test-agent pattern "Test learning content"')
    
    # Test clean command
    print("\n5. Testing memory clean command:")
    run_command("python -m claude_mpm.cli memory clean")
    
    # Test help
    print("\n6. Testing memory help:")
    run_command("python -m claude_mpm.cli memory --help")


if __name__ == "__main__":
    main()