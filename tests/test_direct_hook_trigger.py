#!/usr/bin/env python3
"""Test triggering hooks directly by calling the hook handler."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_direct_hook_call():
    """Test calling the hook handler directly with a TodoWrite event."""
    print("=== Testing Direct Hook Handler Call ===")
    
    try:
        # Find the hook handler
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        hook_handler = project_root / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
        
        if not hook_handler.exists():
            print(f"❌ Hook handler not found at: {hook_handler}")
            return False
        
        print(f"✓ Found hook handler at: {hook_handler}")
        
        # Create a test hook event (simulating TodoWrite)
        test_event = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session-123",
            "timestamp": "2025-07-31T22:00:00Z",
            "tool_name": "TodoWrite",
            "tool_args": {
                "todos": [
                    {
                        "content": "[Research] Test todo for hook system",
                        "status": "pending",
                        "priority": "high",
                        "id": "test-1"
                    }
                ]
            }
        }
        
        # Convert to JSON
        event_json = json.dumps(test_event)
        print(f"✓ Created test event: {test_event['hook_event_name']}")
        
        # Set up environment
        env = os.environ.copy()
        env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
        
        # Call the hook handler
        print("Calling hook handler...")
        result = subprocess.run(
            [sys.executable, str(hook_handler)],
            input=event_json,
            text=True,
            capture_output=True,
            env=env,
            timeout=10
        )
        
        print(f"Hook handler exit code: {result.returncode}")
        if result.stdout:
            print(f"Stdout: {result.stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        
        # Test PostToolUse as well
        print("\nTesting PostToolUse hook...")
        post_event = {
            "hook_event_name": "PostToolUse",
            "session_id": "test-session-123",
            "timestamp": "2025-07-31T22:00:01Z",
            "tool_name": "TodoWrite",
            "exit_code": 0,
            "result": "TodoWrite completed successfully"
        }
        
        post_event_json = json.dumps(post_event)
        
        result2 = subprocess.run(
            [sys.executable, str(hook_handler)],
            input=post_event_json,
            text=True,
            capture_output=True,
            env=env,
            timeout=10
        )
        
        print(f"PostToolUse hook exit code: {result2.returncode}")
        if result2.stdout:
            print(f"Stdout: {result2.stdout}")
        if result2.stderr:
            print(f"Stderr: {result2.stderr}")
        
        return result.returncode == 0 and result2.returncode == 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_response():
    """Test if the Socket.IO server is receiving events."""
    print("\n=== Testing Server Response ===")
    
    try:
        import requests
        
        # Check server status
        response = requests.get("http://localhost:8765/health", timeout=5)
        print(f"✓ Server health check: {response.status_code}")
        print(f"  Response: {response.json()}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Server test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Direct Hook Trigger Test")
    print("=" * 50)
    
    # Test 1: Direct hook handler call
    hook_success = test_direct_hook_call()
    
    # Test 2: Server response
    server_success = test_server_response()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"1. Hook Handler: {'✓ PASS' if hook_success else '❌ FAIL'}")
    print(f"2. Server Response: {'✓ PASS' if server_success else '❌ FAIL'}")
    
    overall_success = hook_success and server_success
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Hook system appears to be working!")
        print("   Now test by opening: http://localhost:8765/dashboard")
        print("   Then run this script to generate test events.")
    else:
        print("\n🔧 Issues detected in hook system.")
        
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())