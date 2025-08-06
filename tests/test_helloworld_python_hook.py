#!/usr/bin/env python3
"""Test script for the Python /helloworld hook."""

import json
import subprocess
import os

def test_hook(prompt):
    """Test the hook with a given prompt."""
    # Test event that Claude Code would send
    test_event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
        "session_id": "test-session",
        "cwd": os.getcwd()
    }
    
    print(f"Testing with prompt: '{prompt}'")
    print(f"Input event: {json.dumps(test_event, indent=2)}")
    
    # Path to the hook
    hook_path = os.path.join(os.path.dirname(__file__), '..', '.claude', 'hooks', 'helloworld_hook.py')
    
    # Run the hook
    result = subprocess.run(
        ['python3', hook_path],
        input=json.dumps(test_event),
        capture_output=True,
        text=True
    )
    
    print(f"\n--- Hook Response ---")
    print(f"Exit code: {result.returncode}")
    
    if result.stderr:
        print(f"Stderr: {result.stderr}")
    
    try:
        response = json.loads(result.stdout)
        print(f"Response: {json.dumps(response, indent=2)}")
        
        # Verify the response
        if prompt.strip() in ['/helloworld', 'Hello World', 'HELLOWORLD_HOOK_TRIGGER']:
            if response.get('action') == 'block' and response.get('alternative') == 'Hello World':
                print(f"\n✅ Test PASSED! The hook correctly intercepted '{prompt}' and returned 'Hello World'")
            else:
                print(f"\n❌ Test FAILED! Expected block action with 'Hello World' alternative")
        else:
            if response.get('action') == 'continue':
                print(f"\n✅ Test PASSED! The hook correctly allowed '{prompt}' to continue")
            else:
                print(f"\n❌ Test FAILED! Expected continue action for non-helloworld prompt")
                
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}")
        print(f"Raw stdout: {result.stdout}")
        
    print("-" * 50)

# Test various prompts
if __name__ == "__main__":
    test_hook("/helloworld")
    test_hook("/helloworld ")  # With trailing space
    test_hook("Hello World")
    test_hook("HELLOWORLD_HOOK_TRIGGER")
    test_hook("What is the weather?")  # Should pass through