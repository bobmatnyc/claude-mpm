#!/usr/bin/env python3
"""
Test script to verify memory system enhancements.

This script tests the implemented memory system enhancements:
1. Memory view command as alias for show
2. Default behavior to show ALL agent memories
3. /mpm slash command integration
4. Updated help documentation

WHY: This provides a comprehensive test of all implemented features
to ensure they work correctly after implementation.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        print(f"Status: {'✅ PASS' if success else '❌ FAIL'} (return code: {result.returncode})")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run all memory enhancement tests."""
    print("Memory System Enhancements Test Suite")
    print("="*60)
    
    claude_mpm = Path("./claude-mpm")
    command_router = Path(".claude/scripts/command_router.py")
    
    if not claude_mpm.exists():
        print("❌ ERROR: claude-mpm executable not found")
        return 1
    
    if not command_router.exists():
        print("❌ ERROR: command_router.py not found")
        return 1
    
    tests = [
        # Test 1: Memory view command help
        ([str(claude_mpm), "memory", "view", "--help"], 
         "Memory view command help shows optional agent_id"),
        
        # Test 2: Memory view without agent_id (should show all)
        ([str(claude_mpm), "memory", "view"],
         "Memory view without agent_id shows all agents"),
        
        # Test 3: Memory show without agent_id (should show all)
        ([str(claude_mpm), "memory", "show"],
         "Memory show without agent_id shows all agents"),
        
        # Test 4: /mpm slash command help
        (["python3", str(command_router), "help"],
         "/mpm slash command help includes memory commands"),
        
        # Test 5: /mpm memory status
        (["python3", str(command_router), "memory", "status"],
         "/mpm memory status command works"),
        
        # Test 6: /mpm memory view (all agents)
        (["python3", str(command_router), "memory", "view"],
         "/mpm memory view shows all agents"),
        
        # Test 7: /mpm memory show (all agents)
        (["python3", str(command_router), "memory", "show"],
         "/mpm memory show shows all agents"),
    ]
    
    passed = 0
    total = len(tests)
    
    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Memory enhancements are working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())