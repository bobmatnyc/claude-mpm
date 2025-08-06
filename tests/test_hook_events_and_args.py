#!/usr/bin/env python3
"""
Test script for new hook events and CLI argument filtering.

This script tests:
1. Hook handler support for new events: Notification, Stop, SubagentStop
2. CLI argument filtering to ensure MPM flags don't reach Claude
"""

import json
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_hook_event_handling():
    """Test that new hook events are properly handled."""
    print("🧪 Testing hook event handling...")
    
    from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
    
    # Test events to simulate
    test_events = [
        {
            'hook_event_name': 'Notification',
            'notification_type': 'user_input_request',
            'message': 'Waiting for user input...',
            'session_id': 'test-session-123',
            'cwd': '/test/dir'
        },
        {
            'hook_event_name': 'Stop',
            'reason': 'completed',
            'stop_type': 'normal',
            'session_id': 'test-session-123',
            'cwd': '/test/dir',
            'final_output': 'Task completed successfully'
        },
        {
            'hook_event_name': 'SubagentStop',
            'agent_type': 'research',
            'agent_id': 'research-001',
            'reason': 'completed',
            'session_id': 'test-session-123',
            'cwd': '/test/dir',
            'results': 'Research findings complete'
        }
    ]
    
    handler = ClaudeHookHandler()
    
    for event in test_events:
        print(f"  Testing {event['hook_event_name']} event...")
        try:
            # Simulate stdin input for the handler
            original_stdin = sys.stdin
            sys.stdin = io.StringIO(json.dumps(event))
            
            # Capture output
            output = io.StringIO()
            with redirect_stdout(output):
                handler.handle()
            
            result = output.getvalue()
            # Should always return continue action
            if '{"action": "continue"}' in result:
                print(f"    ✓ {event['hook_event_name']} handled correctly")
            else:
                print(f"    ❌ {event['hook_event_name']} failed: {result}")
            
            sys.stdin = original_stdin
            
        except Exception as e:
            print(f"    ❌ {event['hook_event_name']} error: {e}")
            sys.stdin = original_stdin

def test_argument_filtering():
    """Test that CLI argument filtering removes all MPM flags."""
    print("\n🧪 Testing CLI argument filtering...")
    
    from claude_mpm.cli.commands.run import filter_claude_mpm_args
    
    # Test cases: [input_args, expected_output, description]
    test_cases = [
        # Basic MPM flags should be filtered
        (['--monitor', '--model', 'sonnet'], ['--model', 'sonnet'], 'Basic monitor flag'),
        (['--resume', 'session-123', '--model', 'claude-3'], ['--model', 'claude-3'], 'Resume flag'),
        (['--monitor', '--temperature', '0.5'], ['--temperature', '0.5'], 'Monitor flag'),
        
        # Flags with values should filter both flag and value
        (['--websocket-port', '8080', '--model', 'sonnet'], ['--model', 'sonnet'], 'Flag with value'),
        (['--logging', 'DEBUG', '--temperature', '0.1'], ['--temperature', '0.1'], 'Logging with value'),
        (['-i', 'test input', '--model', 'haiku'], ['--model', 'haiku'], 'Short flag with value'),
        
        # Complex mixed cases
        (['--monitor', '--websocket-port', '9000', '--model', 'sonnet', '--no-hooks', '--temperature', '0.7'], 
         ['--model', 'sonnet', '--temperature', '0.7'], 'Multiple MPM flags mixed with Claude flags'),
        
        # No MPM flags should pass through unchanged
        (['--model', 'claude-3', '--temperature', '0.5', '--max-tokens', '1000'], 
         ['--model', 'claude-3', '--temperature', '0.5', '--max-tokens', '1000'], 'No MPM flags'),
        
        # All MPM flags should result in empty output
        (['--monitor', '--no-hooks', '--resume', '--debug'], [], 'Only MPM flags'),
        
        # Edge cases
        ([], [], 'Empty input'),
        (['--websocket-port'], [], 'Flag with missing value (edge case)'),
    ]
    
    for input_args, expected, description in test_cases:
        print(f"  Testing: {description}")
        try:
            result = filter_claude_mpm_args(input_args)
            if result == expected:
                print(f"    ✓ Passed: {input_args} → {result}")
            else:
                print(f"    ❌ Failed: {input_args} → {result} (expected: {expected})")
        except Exception as e:
            print(f"    ❌ Error: {e}")

def test_specific_problematic_flags():
    """Test specific flags that were causing issues."""
    print("\n🧪 Testing specific problematic flags...")
    
    from claude_mpm.cli.commands.run import filter_claude_mpm_args
    
    # These are the flags mentioned in the issue
    problematic_cases = [
        # --monitor should be filtered
        (['--monitor', '--model', 'sonnet'], ['--model', 'sonnet'], '--monitor flag'),
        # --resume should be filtered
        (['--resume', 'session-123', '--temperature', '0.5'], ['--temperature', '0.5'], '--resume flag'),
        # Combination of both
        (['--monitor', '--resume', 'session-456', '--model', 'claude-3'], ['--model', 'claude-3'], 'Both flags'),
    ]
    
    for input_args, expected, description in problematic_cases:
        print(f"  Testing: {description}")
        result = filter_claude_mpm_args(input_args)
        if result == expected:
            print(f"    ✓ Correctly filtered: {input_args} → {result}")
        else:
            print(f"    ❌ Filtering failed: {input_args} → {result} (expected: {expected})")

def main():
    """Run all tests."""
    print("🚀 Testing Hook Events and CLI Argument Filtering")
    print("=" * 60)
    
    try:
        test_hook_event_handling()
        test_argument_filtering()
        test_specific_problematic_flags()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("\n💡 Next steps:")
        print("  1. Test with actual Claude CLI to ensure no errors")
        print("  2. Monitor hook events in Socket.IO dashboard")
        print("  3. Verify --monitor and --resume flags work as expected")
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())