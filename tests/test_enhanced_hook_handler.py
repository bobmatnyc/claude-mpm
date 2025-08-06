#!/usr/bin/env python3
"""Test script for the enhanced hook handler to verify data capture."""

import json
import subprocess
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


def test_hook_handler_with_event(event_name, event_data):
    """Test the hook handler with a specific event."""
    print(f"\n🧪 Testing {event_name} hook...")
    
    # Path to the hook handler
    hook_handler_path = project_root / 'src' / 'claude_mpm' / 'hooks' / 'claude_hooks' / 'hook_handler.py'
    
    # Create the test event
    test_event = {
        "hook_event_name": event_name,
        "session_id": "test-session-123",
        "cwd": str(project_root),
        **event_data
    }
    
    print(f"📋 Input event: {json.dumps(test_event, indent=2)}")
    
    try:
        # Set environment variables for testing
        env = os.environ.copy()
        env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
        env['PYTHONPATH'] = str(project_root / 'src')
        
        # Run the hook handler
        process = subprocess.Popen(
            [sys.executable, str(hook_handler_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Send the event data
        stdout, stderr = process.communicate(input=json.dumps(test_event))
        
        print(f"📤 Handler output: {stdout.strip()}")
        if stderr.strip():
            print(f"🔧 Debug output: {stderr.strip()}")
        
        return process.returncode == 0
        
    except Exception as e:
        print(f"❌ Error testing hook handler: {e}")
        return False


def main():
    """Run comprehensive tests of the enhanced hook handler."""
    print("🚀 Testing Enhanced Claude Hook Handler")
    print("=" * 50)
    
    # Test UserPromptSubmit
    success1 = test_hook_handler_with_event("UserPromptSubmit", {
        "prompt": "Please help me debug this urgent error in my Python script. There's a bug in the authentication function."
    })
    
    # Test PreToolUse - Write operation
    success2 = test_hook_handler_with_event("PreToolUse", {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "/Users/test/project/test.py",
            "content": "print('Hello, World!')\n# This is a test file"
        }
    })
    
    # Test PreToolUse - Bash operation (potentially risky)
    success3 = test_hook_handler_with_event("PreToolUse", {
        "tool_name": "Bash",
        "tool_input": {
            "command": "sudo rm -rf /important/data",
            "timeout": 30000
        }
    })
    
    # Test PostToolUse
    success4 = test_hook_handler_with_event("PostToolUse", {
        "tool_name": "Read",
        "exit_code": 0,
        "output": "File contents here\nLine 2\nLine 3"
    })
    
    # Test PostToolUse with error
    success5 = test_hook_handler_with_event("PostToolUse", {
        "tool_name": "Bash",
        "exit_code": 1,
        "error": "Command failed: permission denied"
    })
    
    # Summary
    total_tests = 5
    passed_tests = sum([success1, success2, success3, success4, success5])
    
    print(f"\n📊 Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("✅ All tests passed! Enhanced hook handler is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)