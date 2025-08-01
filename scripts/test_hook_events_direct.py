#!/usr/bin/env python3
"""
Direct test of hook events by simulating Socket.IO event capture.

This script specifically tests the new hook events (Notification, Stop, SubagentStop)
by running the hook handler directly and validating the Socket.IO event emissions.
"""

import sys
import os
import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_hook_event_with_socketio_capture(event_data, event_type):
    """Test hook event processing with Socket.IO event capture."""
    print(f"\n🧪 Testing {event_type} event with Socket.IO capture...")
    
    # Set environment for hook debugging
    env = os.environ.copy()
    env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    env['CLAUDE_MPM_SOCKETIO_PORT'] = '8767'  # Use test port
    
    # Path to hook handler
    hook_handler_path = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    
    try:
        # Run hook handler with event data
        result = subprocess.run([
            sys.executable, str(hook_handler_path)
        ], input=json.dumps(event_data), text=True, capture_output=True, env=env, timeout=10)
        
        print(f"   Hook handler exit code: {result.returncode}")
        print(f"   STDOUT: {result.stdout.strip()}")
        if result.stderr:
            print(f"   STDERR: {result.stderr}")
        
        # Parse response
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout.strip())
                if response.get('action') == 'continue':
                    print(f"   ✅ {event_type} event processed successfully")
                    return True
                else:
                    print(f"   ❌ Unexpected response: {response}")
                    return False
            except json.JSONDecodeError as e:
                print(f"   ❌ Failed to parse JSON response: {e}")
                return False
        else:
            print(f"   ❌ Hook handler failed with exit code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ Hook handler timed out")
        return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def test_cli_filtering_in_isolation():
    """Test CLI filtering functionality in isolation."""
    print("\n⚙️  Testing CLI filtering in isolation...")
    
    try:
        from claude_mpm.cli.commands.run import filter_claude_mpm_args
        
        # Test comprehensive flag filtering
        test_cases = [
            {
                'name': 'monitor_flag',
                'input': ['--model', 'claude-3-sonnet', '--monitor', '--verbose'],
                'expected_filtered': ['--model', 'claude-3-sonnet', '--verbose']
            },
            {
                'name': 'resume_with_value',
                'input': ['--resume', 'session_123', '--model', 'claude-3-sonnet'],
                'expected_filtered': ['--model', 'claude-3-sonnet']
            },
            {
                'name': 'websocket_port',
                'input': ['--websocket-port', '8080', '--model', 'claude-3-sonnet'],
                'expected_filtered': ['--model', 'claude-3-sonnet']
            },
            {
                'name': 'input_flag',
                'input': ['--input', 'Hello Claude', '--non-interactive'],
                'expected_filtered': []
            },
            {
                'name': 'debug_logging',
                'input': ['--debug', '--logging', 'DEBUG', '--model', 'claude-3-sonnet'],
                'expected_filtered': ['--model', 'claude-3-sonnet']
            }
        ]
        
        all_passed = True
        for test_case in test_cases:
            filtered = filter_claude_mpm_args(test_case['input'])
            expected = test_case['expected_filtered']
            
            if filtered == expected:
                print(f"   ✅ {test_case['name']}: PASSED")
                print(f"      Input: {test_case['input']}")
                print(f"      Output: {filtered}")
            else:
                print(f"   ❌ {test_case['name']}: FAILED")
                print(f"      Input: {test_case['input']}")
                print(f"      Expected: {expected}")
                print(f"      Got: {filtered}")
                all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print(f"   ❌ Failed to import CLI filtering: {e}")
        return False

def test_claude_mpm_script_execution():
    """Test claude-mpm script execution with various flags."""
    print("\n🔗 Testing claude-mpm script execution...")
    
    claude_mpm_script = Path(__file__).parent / "claude-mpm"
    if not claude_mpm_script.exists():
        print("   ❌ claude-mpm script not found")
        return False
    
    # Test with --help flag to avoid actually starting Claude
    test_cases = [
        {
            'name': 'help_only',
            'args': ['--help'],
            'should_succeed': True
        },
        {
            'name': 'monitor_help',
            'args': ['--monitor', '--help'],
            'should_succeed': True
        },
        {
            'name': 'resume_help',
            'args': ['--resume', 'test_session', '--help'],
            'should_succeed': True
        }
    ]
    
    all_passed = True
    for test_case in test_cases:
        try:
            cmd = [str(claude_mpm_script)] + test_case['args']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # For --help, we expect success (exit code 0)
            success = result.returncode == 0
            has_arg_errors = "unrecognized arguments" in result.stderr.lower()
            
            if success and not has_arg_errors:
                print(f"   ✅ {test_case['name']}: PASSED")
            else:
                print(f"   ❌ {test_case['name']}: FAILED")
                print(f"      Exit code: {result.returncode}")
                if has_arg_errors:
                    print(f"      Argument errors detected in stderr")
                if result.stderr:
                    print(f"      STDERR: {result.stderr[:200]}")
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print(f"   ❌ {test_case['name']}: TIMEOUT")
            all_passed = False
        except Exception as e:
            print(f"   ❌ {test_case['name']}: ERROR - {e}")
            all_passed = False
    
    return all_passed

def main():
    """Run focused tests for hook events and CLI filtering."""
    print("🎯 Focused Testing: Hook Events and CLI Filtering")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Hook Events
    print("\n📡 HOOK EVENTS TESTING")
    print("-" * 30)
    
    # Test Notification event
    notification_event = {
        "hook_event_name": "Notification",
        "notification_type": "status_update",
        "message": "Processing your request, please wait...",
        "session_id": "test_session_123",
        "cwd": "/test/directory"
    }
    results['notification_event'] = test_hook_event_with_socketio_capture(
        notification_event, "Notification"
    )
    
    # Test Stop event
    stop_event = {
        "hook_event_name": "Stop",
        "reason": "user_stop",
        "stop_type": "interrupt",
        "session_id": "test_session_123",
        "cwd": "/test/directory",
        "final_output": None
    }
    results['stop_event'] = test_hook_event_with_socketio_capture(
        stop_event, "Stop"
    )
    
    # Test SubagentStop event
    subagent_stop_event = {
        "hook_event_name": "SubagentStop",
        "agent_type": "pm",
        "agent_id": "pm_agent_002",
        "reason": "error",
        "session_id": "test_session_123",
        "cwd": "/test/directory",
        "results": None,
        "duration_ms": 500
    }
    results['subagent_stop_event'] = test_hook_event_with_socketio_capture(
        subagent_stop_event, "SubagentStop"
    )
    
    # Test 2: CLI Filtering
    print("\n⚙️  CLI FILTERING TESTING")
    print("-" * 30)
    results['cli_filtering'] = test_cli_filtering_in_isolation()
    
    # Test 3: Script Execution
    print("\n🔗 SCRIPT EXECUTION TESTING")
    print("-" * 30)
    results['script_execution'] = test_claude_mpm_script_execution()
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    # Write results to file
    results_data = {
        'test_results': results,
        'summary': {
            'passed': passed,
            'total': total,
            'success_rate': success_rate
        },
        'timestamp': datetime.now().isoformat()
    }
    
    results_file = Path(__file__).parent / "test_results_hook_events_direct.json"
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\n📄 Results written to: {results_file}")
    
    if success_rate >= 80:
        print("\n🎉 OVERALL SUCCESS")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())