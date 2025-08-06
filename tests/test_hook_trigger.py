#!/usr/bin/env python3
"""Simple test to verify hook system is working."""

import json
import os
import sys

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

def test_user_prompt_hook():
    """Test user prompt hook event."""
    print("Testing user prompt hook...")
    
    # Create test event
    test_event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Test message to trigger hooks",
        "session_id": "test-session-123",
        "cwd": os.getcwd()
    }
    
    # Enable debug
    os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    
    # Create handler and process event
    handler = ClaudeHookHandler()
    
    # Simulate stdin input
    original_stdin = sys.stdin
    sys.stdin = type('', (), {'read': lambda: json.dumps(test_event)})()
    
    try:
        handler.handle()
        print("✓ Hook handler executed successfully")
    except Exception as e:
        print(f"✗ Hook handler failed: {e}")
    finally:
        sys.stdin = original_stdin

def test_tool_hooks():
    """Test pre and post tool hooks."""
    print("\nTesting tool hooks...")
    
    # Pre-tool event
    pre_tool_event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo 'Hello from test'"},
        "session_id": "test-session-123",
        "cwd": os.getcwd()
    }
    
    # Post-tool event
    post_tool_event = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "exit_code": 0,
        "output": "Hello from test",
        "session_id": "test-session-123",
        "cwd": os.getcwd()
    }
    
    handler = ClaudeHookHandler()
    
    for event_name, event in [("PreToolUse", pre_tool_event), ("PostToolUse", post_tool_event)]:
        original_stdin = sys.stdin
        sys.stdin = type('', (), {'read': lambda e=event: json.dumps(e)})()
        
        try:
            handler.handle()
            print(f"✓ {event_name} hook executed successfully")
        except Exception as e:
            print(f"✗ {event_name} hook failed: {e}")
        finally:
            sys.stdin = original_stdin

if __name__ == "__main__":
    print("Hook System Test")
    print("=" * 50)
    test_user_prompt_hook()
    test_tool_hooks()
    print("\nTest complete!")