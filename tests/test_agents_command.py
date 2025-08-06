#!/usr/bin/env python3
"""Test script for /mpm agents command functionality.

WHY: This script was created to verify that the /mpm agents command correctly
displays agent version information using the same underlying function as the
startup display, ensuring consistency across the application.
"""

import subprocess
import sys
from pathlib import Path

def test_mpm_agents_command():
    """Test the /mpm agents command."""
    print("Testing /mpm agents command...")
    print("=" * 60)
    
    # Test 1: Run claude-mpm agents (without prefix)
    print("\n1. Testing: claude-mpm agents")
    result = subprocess.run([sys.executable, "-m", "claude_mpm.cli", "agents"], 
                          capture_output=True, text=True)
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    print(f"Return code: {result.returncode}")
    
    # Test 2: Run claude-mpm --mpm:agents (with prefix)
    print("\n" + "=" * 60)
    print("2. Testing: claude-mpm --mpm:agents")
    result = subprocess.run([sys.executable, "-m", "claude_mpm.cli", "--mpm:agents"], 
                          capture_output=True, text=True)
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    print(f"Return code: {result.returncode}")
    
    # Test 3: Compare with startup display by running in non-interactive mode
    print("\n" + "=" * 60)
    print("3. Comparing with startup display (non-interactive mode)")
    result = subprocess.run([sys.executable, "-m", "claude_mpm.cli", "run", "--non-interactive", "-i", "exit"], 
                          capture_output=True, text=True)
    
    # Extract the Deployed Agent Versions section from startup
    lines = result.stdout.split('\n')
    in_agent_section = False
    startup_display = []
    
    for line in lines:
        if "Deployed Agent Versions:" in line:
            in_agent_section = True
        if in_agent_section:
            startup_display.append(line)
            if line.strip() == "-" * 40 and len(startup_display) > 1:
                break
    
    if startup_display:
        print("Startup display found:")
        print('\n'.join(startup_display))
    else:
        print("No startup display found")
    
    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == "__main__":
    test_mpm_agents_command()