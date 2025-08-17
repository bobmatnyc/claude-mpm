#!/usr/bin/env python3
"""
Test script for MCP CLI commands.

WHY: This script validates that all MCP CLI commands are properly
registered and accessible through the claude-mpm CLI.
"""

import subprocess
import sys
from pathlib import Path

def test_mcp_commands():
    """Test all MCP CLI commands are accessible."""
    
    # Test command list
    commands = [
        ["mcp", "--help"],
        ["mcp", "install", "--help"],
        ["mcp", "start", "--help"],
        ["mcp", "stop", "--help"],
        ["mcp", "status", "--help"],
        ["mcp", "tools", "--help"],
        ["mcp", "register", "--help"],
        ["mcp", "test", "--help"],
        ["mcp", "config", "--help"],
    ]
    
    print("Testing MCP CLI Commands")
    print("=" * 50)
    
    all_passed = True
    
    for cmd_parts in commands:
        cmd = ["python", "-m", "claude_mpm.cli"] + cmd_parts
        cmd_str = " ".join(cmd_parts)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print(f"✅ {cmd_str}")
            else:
                print(f"❌ {cmd_str}")
                print(f"   Error: {result.stderr}")
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print(f"❌ {cmd_str} (timeout)")
            all_passed = False
        except Exception as e:
            print(f"❌ {cmd_str}")
            print(f"   Exception: {e}")
            all_passed = False
    
    print()
    
    # Test actual command execution (non-destructive)
    print("Testing MCP Command Execution")
    print("=" * 50)
    
    # Test status command
    cmd = ["python", "-m", "claude_mpm.cli", "mcp", "status"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ mcp status executed successfully")
            print("Output:")
            print(result.stdout)
        else:
            print("❌ mcp status failed")
            print(f"Error: {result.stderr}")
            all_passed = False
    except Exception as e:
        print(f"❌ mcp status exception: {e}")
        all_passed = False
    
    print()
    if all_passed:
        print("✅ All MCP CLI commands are working correctly!")
        return 0
    else:
        print("❌ Some MCP CLI commands failed!")
        return 1

if __name__ == "__main__":
    sys.exit(test_mcp_commands())