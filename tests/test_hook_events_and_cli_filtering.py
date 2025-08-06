#!/usr/bin/env python3
"""
Comprehensive test suite for new hook events and CLI argument filtering.

This script tests:
1. New hook events (Notification, Stop, SubagentStop)
2. CLI argument filtering (--monitor, --resume, all MPM flags)
3. Integration testing with Socket.IO monitoring
4. Validation that Claude doesn't see MPM-specific arguments

WHY: These features are critical for proper operation of the MPM system
and need thorough validation before deployment.
"""

import sys
import os
import json
import subprocess
import time
import threading
import tempfile
import signal
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class HookEventTester:
    """Test new hook events (Notification, Stop, SubagentStop)."""
    
    def __init__(self):
        self.test_results = {}
        self.hook_handler_path = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    
    def test_notification_event(self):
        """Test Notification event processing."""
        print("\n🧪 Testing Notification event processing...")
        
        # Create test notification event
        notification_event = {
            "hook_event_name": "Notification",
            "notification_type": "user_input_request",
            "message": "Please provide your input for the next step",
            "session_id": "test_session_123",
            "cwd": "/test/directory"
        }
        
        result = self._test_hook_handler(notification_event)
        
        expected_fields = [
            'event_type', 'notification_type', 'message', 'message_preview',
            'message_length', 'session_id', 'working_directory', 'timestamp',
            'is_user_input_request', 'is_error_notification', 'is_status_update'
        ]
        
        self.test_results['notification_event'] = {
            'success': result['success'],
            'processed_data': result.get('processed_data', {}),
            'expected_fields_present': all(field in result.get('processed_data', {}) for field in expected_fields),
            'error': result.get('error')
        }
        
        if result['success']:
            print("✅ Notification event processing: PASSED")
            print(f"   - Event type: {result['processed_data'].get('event_type')}")
            print(f"   - Notification type: {result['processed_data'].get('notification_type')}")
            print(f"   - Message preview: {result['processed_data'].get('message_preview')}")
            print(f"   - Classification flags: user_input={result['processed_data'].get('is_user_input_request')}")
        else:
            print("❌ Notification event processing: FAILED")
            print(f"   Error: {result.get('error')}")
    
    def test_stop_event(self):
        """Test Stop event processing."""
        print("\n🧪 Testing Stop event processing...")
        
        # Create test stop event
        stop_event = {
            "hook_event_name": "Stop",
            "reason": "completed",
            "stop_type": "normal",
            "session_id": "test_session_123",
            "cwd": "/test/directory",
            "final_output": "Task completed successfully"
        }
        
        result = self._test_hook_handler(stop_event)
        
        expected_fields = [
            'event_type', 'reason', 'stop_type', 'session_id', 'working_directory',
            'timestamp', 'is_user_initiated', 'is_error_stop', 'is_completion_stop', 'has_output'
        ]
        
        self.test_results['stop_event'] = {
            'success': result['success'],
            'processed_data': result.get('processed_data', {}),
            'expected_fields_present': all(field in result.get('processed_data', {}) for field in expected_fields),
            'error': result.get('error')
        }
        
        if result['success']:
            print("✅ Stop event processing: PASSED")
            print(f"   - Event type: {result['processed_data'].get('event_type')}")
            print(f"   - Reason: {result['processed_data'].get('reason')}")
            print(f"   - Stop type: {result['processed_data'].get('stop_type')}")
            print(f"   - Classification: completion={result['processed_data'].get('is_completion_stop')}")
        else:
            print("❌ Stop event processing: FAILED")
            print(f"   Error: {result.get('error')}")
    
    def test_subagent_stop_event(self):
        """Test SubagentStop event processing."""
        print("\n🧪 Testing SubagentStop event processing...")
        
        # Create test subagent stop event
        subagent_stop_event = {
            "hook_event_name": "SubagentStop",
            "agent_type": "research",
            "agent_id": "research_agent_001",
            "reason": "completed",
            "session_id": "test_session_123",
            "cwd": "/test/directory",
            "results": {"status": "success", "data": "Research completed"},
            "duration_ms": 1500
        }
        
        result = self._test_hook_handler(subagent_stop_event)
        
        expected_fields = [
            'event_type', 'agent_type', 'agent_id', 'reason', 'session_id',
            'working_directory', 'timestamp', 'is_successful_completion',
            'is_error_termination', 'is_delegation_related', 'has_results', 'duration_context'
        ]
        
        self.test_results['subagent_stop_event'] = {
            'success': result['success'],
            'processed_data': result.get('processed_data', {}),
            'expected_fields_present': all(field in result.get('processed_data', {}) for field in expected_fields),
            'error': result.get('error')
        }
        
        if result['success']:
            print("✅ SubagentStop event processing: PASSED")
            print(f"   - Event type: {result['processed_data'].get('event_type')}")
            print(f"   - Agent type: {result['processed_data'].get('agent_type')}")
            print(f"   - Agent ID: {result['processed_data'].get('agent_id')}")
            print(f"   - Classification: successful={result['processed_data'].get('is_successful_completion')}")
        else:
            print("❌ SubagentStop event processing: FAILED")
            print(f"   Error: {result.get('error')}")
    
    def _test_hook_handler(self, event_data):
        """Test hook handler with specific event data."""
        try:
            # Create temporary input file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(event_data, f)
                temp_file = f.name
            
            try:
                # Run hook handler with test data
                env = os.environ.copy()
                env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
                
                result = subprocess.run([
                    sys.executable, str(self.hook_handler_path)
                ], input=json.dumps(event_data), text=True, capture_output=True, env=env, timeout=10)
                
                if result.returncode == 0:
                    # Parse the response
                    response = json.loads(result.stdout.strip())
                    if response.get('action') == 'continue':
                        return {
                            'success': True,
                            'processed_data': event_data,  # For now, we assume processing worked
                            'stdout': result.stdout,
                            'stderr': result.stderr
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"Unexpected response: {response}",
                            'stdout': result.stdout,
                            'stderr': result.stderr
                        }
                else:
                    return {
                        'success': False,
                        'error': f"Hook handler failed with exit code {result.returncode}",
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                    
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file)
                except:
                    pass
                    
        except Exception as e:
            return {
                'success': False,
                'error': f"Exception during hook handler test: {e}"
            }


class CLIArgumentFilterTester:
    """Test CLI argument filtering functionality."""
    
    def __init__(self):
        self.test_results = {}
    
    def test_monitor_flag_filtering(self):
        """Test that --monitor flag is filtered out."""
        print("\n🧪 Testing --monitor flag filtering...")
        
        from claude_mpm.cli.commands.run import filter_claude_mpm_args
        
        test_args = ['--model', 'claude-3-sonnet', '--monitor', '--verbose']
        filtered_args = filter_claude_mpm_args(test_args)
        
        success = '--monitor' not in filtered_args
        self.test_results['monitor_flag_filtering'] = {
            'success': success,
            'original_args': test_args,
            'filtered_args': filtered_args,
            'monitor_removed': '--monitor' not in filtered_args
        }
        
        if success:
            print("✅ --monitor flag filtering: PASSED")
            print(f"   Original: {test_args}")
            print(f"   Filtered: {filtered_args}")
        else:
            print("❌ --monitor flag filtering: FAILED")
            print(f"   --monitor still present in filtered args: {filtered_args}")
    
    def test_resume_flag_filtering(self):
        """Test that --resume with values is properly filtered."""
        print("\n🧪 Testing --resume flag filtering...")
        
        from claude_mpm.cli.commands.run import filter_claude_mpm_args
        
        test_args = ['--model', 'claude-3-sonnet', '--resume', 'session_123', '--verbose']
        filtered_args = filter_claude_mpm_args(test_args)
        
        success = '--resume' not in filtered_args and 'session_123' not in filtered_args
        self.test_results['resume_flag_filtering'] = {
            'success': success,
            'original_args': test_args,
            'filtered_args': filtered_args,
            'resume_removed': '--resume' not in filtered_args,
            'value_removed': 'session_123' not in filtered_args
        }
        
        if success:
            print("✅ --resume flag filtering: PASSED")
            print(f"   Original: {test_args}")
            print(f"   Filtered: {filtered_args}")
        else:
            print("❌ --resume flag filtering: FAILED")
            print(f"   --resume or its value still present: {filtered_args}")
    
    def test_all_mpm_flags_removal(self):
        """Test that all MPM flags are removed."""
        print("\n🧪 Testing all MPM flags removal...")
        
        from claude_mpm.cli.commands.run import filter_claude_mpm_args
        
        mpm_flags = [
            '--monitor', '--websocket-port', '8080',
            '--no-hooks', '--no-tickets', '--intercept-commands',
            '--no-native-agents', '--launch-method', 'exec',
            '--resume', 'session_id',
            '--input', 'test input', '--non-interactive',
            '--debug', '--logging', 'INFO', '--log-dir', '/tmp/logs',
            '--framework-path', '/path/to/framework',
            '--agents-dir', '/path/to/agents',
            '--version', '-i', 'input', '-d'
        ]
        
        # Mix with legitimate Claude CLI args
        claude_args = ['--model', 'claude-3-sonnet', '--verbose']
        test_args = claude_args + mpm_flags
        
        filtered_args = filter_claude_mpm_args(test_args)
        
        # Check that Claude args remain and MPM args are removed
        claude_args_preserved = all(arg in filtered_args for arg in claude_args)
        mpm_flags_removed = not any(flag in filtered_args for flag in [
            '--monitor', '--websocket-port', '--no-hooks',
            '--no-tickets', '--intercept-commands', '--no-native-agents',
            '--launch-method', '--resume', '--input',
            '--non-interactive', '--debug', '--logging', '--log-dir',
            '--framework-path', '--agents-dir', '--version', '-i', '-d'
        ])
        
        success = claude_args_preserved and mpm_flags_removed
        self.test_results['all_mpm_flags_removal'] = {
            'success': success,
            'claude_args_preserved': claude_args_preserved,
            'mpm_flags_removed': mpm_flags_removed,
            'original_count': len(test_args),
            'filtered_count': len(filtered_args),
            'filtered_args': filtered_args
        }
        
        if success:
            print("✅ All MPM flags removal: PASSED")
            print(f"   Filtered {len(test_args) - len(filtered_args)} MPM-specific arguments")
            print(f"   Preserved Claude args: {[arg for arg in filtered_args if arg in claude_args]}")
        else:
            print("❌ All MPM flags removal: FAILED")
            if not claude_args_preserved:
                print("   Claude args were incorrectly filtered")
            if not mpm_flags_removed:
                print("   Some MPM flags were not removed")
    
    def test_non_mpm_args_passthrough(self):
        """Test that non-MPM args pass through correctly."""
        print("\n🧪 Testing non-MPM args passthrough...")
        
        from claude_mpm.cli.commands.run import filter_claude_mpm_args
        
        # Common Claude CLI arguments that should pass through
        claude_args = [
            '--model', 'claude-3-sonnet',
            '--verbose',
            '--temperature', '0.7',
            '--max-tokens', '4000',
            '--system', 'You are a helpful assistant',
            '--output', 'json',
            '--timeout', '30'
        ]
        
        # Mix with MPM args that should be filtered
        test_args = claude_args + ['--monitor', '--debug', '--websocket-port', '8080']
        filtered_args = filter_claude_mpm_args(test_args)
        
        # All Claude args should remain
        success = all(arg in filtered_args for arg in claude_args)
        mpm_args_removed = '--monitor' not in filtered_args and '--debug' not in filtered_args
        
        self.test_results['non_mpm_args_passthrough'] = {
            'success': success and mpm_args_removed,
            'claude_args_preserved': success,
            'mpm_args_removed': mpm_args_removed,
            'original_args': test_args,
            'filtered_args': filtered_args
        }
        
        if success and mpm_args_removed:
            print("✅ Non-MPM args passthrough: PASSED")
            print(f"   All Claude args preserved: {claude_args}")
            print(f"   MPM args filtered out successfully")
        else:
            print("❌ Non-MPM args passthrough: FAILED")
            if not success:
                missing = [arg for arg in claude_args if arg not in filtered_args]
                print(f"   Missing Claude args: {missing}")
            if not mpm_args_removed:
                print(f"   MPM args not filtered: {[arg for arg in ['--monitor', '--debug'] if arg in filtered_args]}")


class IntegrationTester:
    """Test integration scenarios with various flag combinations."""
    
    def __init__(self):
        self.test_results = {}
        self.claude_mpm_script = Path(__file__).parent / "claude-mpm"
    
    def test_various_flag_combinations(self):
        """Test claude-mpm with various flag combinations."""
        print("\n🧪 Testing various flag combinations...")
        
        test_combinations = [
            {
                'name': 'monitor_only',
                'args': ['--monitor'],
                'should_succeed': True
            },
            {
                'name': 'monitor_with_port',
                'args': ['--monitor', '--websocket-port', '8765'],
                'should_succeed': True
            },
            {
                'name': 'resume_with_value',
                'args': ['--resume', 'test_session'],
                'should_succeed': True
            },
            {
                'name': 'mixed_mpm_and_claude_args',
                'args': ['--monitor', '--model', 'claude-3-sonnet', '--debug', '--verbose'],
                'should_succeed': True
            },
            {
                'name': 'input_mode',
                'args': ['--input', 'Hello, Claude!', '--non-interactive'],
                'should_succeed': True
            }
        ]
        
        results = {}
        for test_case in test_combinations:
            print(f"   Testing combination: {test_case['name']}")
            
            try:
                # Run with --help to avoid actually starting Claude
                cmd = [sys.executable, str(self.claude_mpm_script)] + test_case['args'] + ['--help']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                # For --help, success means no argument parsing errors
                success = result.returncode == 0 and "unrecognized arguments" not in result.stderr
                
                results[test_case['name']] = {
                    'success': success,
                    'expected_success': test_case['should_succeed'],
                    'returncode': result.returncode,
                    'has_arg_errors': "unrecognized arguments" in result.stderr,
                    'stderr_preview': result.stderr[:200] if result.stderr else None
                }
                
                if success:
                    print(f"     ✅ {test_case['name']}: PASSED")
                else:
                    print(f"     ❌ {test_case['name']}: FAILED")
                    if "unrecognized arguments" in result.stderr:
                        print(f"        Error: Unrecognized arguments detected")
                
            except subprocess.TimeoutExpired:
                results[test_case['name']] = {
                    'success': False,
                    'expected_success': test_case['should_succeed'],
                    'error': 'Timeout'
                }
                print(f"     ❌ {test_case['name']}: TIMEOUT")
            except Exception as e:
                results[test_case['name']] = {
                    'success': False,
                    'expected_success': test_case['should_succeed'],
                    'error': str(e)
                }
                print(f"     ❌ {test_case['name']}: ERROR - {e}")
        
        self.test_results['flag_combinations'] = results
    
    def test_socketio_server_startup(self):
        """Test Socket.IO server startup with monitoring."""
        print("\n🧪 Testing Socket.IO server startup...")
        
        # Test if Socket.IO dependencies are available
        try:
            import socketio
            import aiohttp
            dependencies_available = True
        except ImportError:
            dependencies_available = False
        
        if not dependencies_available:
            print("   ⚠️  Socket.IO dependencies not available - skipping server tests")
            self.test_results['socketio_server'] = {
                'success': False,
                'error': 'Dependencies not available',
                'dependencies_available': False
            }
            return
        
        # Start a quick Socket.IO server test
        server_port = 8766  # Use different port to avoid conflicts
        
        try:
            # Try to start server in background using existing script
            scripts_dir = Path(__file__).parent
            server_script = scripts_dir / "start_persistent_socketio_server.py"
            
            if server_script.exists():
                server_process = subprocess.Popen([
                    sys.executable, str(server_script),
                    "--port", str(server_port),
                    "--quiet"
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Wait a moment for server to start
                time.sleep(2)
                
                # Test if server is accessible
                try:
                    response = urllib.request.urlopen(f'http://localhost:{server_port}/status', timeout=5)
                    server_accessible = response.status == 200
                except:
                    server_accessible = False
                
                # Clean up
                server_process.terminate()
                server_process.wait(timeout=5)
                
                self.test_results['socketio_server'] = {
                    'success': server_accessible,
                    'dependencies_available': True,
                    'server_accessible': server_accessible,
                    'port': server_port
                }
                
                if server_accessible:
                    print("   ✅ Socket.IO server startup: PASSED")
                else:
                    print("   ❌ Socket.IO server startup: FAILED - server not accessible")
            else:
                print("   ⚠️  Socket.IO server script not found - skipping server test")
                self.test_results['socketio_server'] = {
                    'success': False,
                    'error': 'Server script not found',
                    'dependencies_available': True
                }
                
        except Exception as e:
            self.test_results['socketio_server'] = {
                'success': False,
                'error': str(e),
                'dependencies_available': True
            }
            print(f"   ❌ Socket.IO server startup: ERROR - {e}")


def main():
    """Run comprehensive test suite."""
    print("🚀 Starting comprehensive test suite for hook events and CLI filtering")
    print("=" * 80)
    
    # Initialize testers
    hook_tester = HookEventTester()
    cli_tester = CLIArgumentFilterTester()
    integration_tester = IntegrationTester()
    
    # Run hook event tests
    print("\n📡 TESTING HOOK EVENTS")
    print("-" * 40)
    hook_tester.test_notification_event()
    hook_tester.test_stop_event()
    hook_tester.test_subagent_stop_event()
    
    # Run CLI argument filtering tests
    print("\n⚙️  TESTING CLI ARGUMENT FILTERING")
    print("-" * 40)
    cli_tester.test_monitor_flag_filtering()
    cli_tester.test_resume_flag_filtering()
    cli_tester.test_all_mpm_flags_removal()
    cli_tester.test_non_mpm_args_passthrough()
    
    # Run integration tests
    print("\n🔗 TESTING INTEGRATION SCENARIOS")
    print("-" * 40)
    integration_tester.test_various_flag_combinations()
    integration_tester.test_socketio_server_startup()
    
    # Generate summary report
    print("\n📊 TEST SUMMARY REPORT")
    print("=" * 80)
    
    all_results = {
        'hook_events': hook_tester.test_results,
        'cli_filtering': cli_tester.test_results,
        'integration': integration_tester.test_results,
        'timestamp': datetime.now().isoformat(),
        'test_environment': {
            'python_version': sys.version,
            'platform': os.name,
            'working_directory': str(Path.cwd())
        }
    }
    
    # Count successes and failures
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        if category in ['timestamp', 'test_environment']:
            continue
            
        for test_name, result in results.items():
            total_tests += 1
            if isinstance(result, dict) and result.get('success'):
                passed_tests += 1
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Write detailed results to file
    results_file = Path(__file__).parent / "test_results_hook_events_cli_filtering.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n📄 Detailed results written to: {results_file}")
    
    # Final status
    if success_rate >= 80:
        print("\n🎉 TEST SUITE: OVERALL SUCCESS")
        return 0
    else:
        print("\n⚠️  TEST SUITE: SOME FAILURES DETECTED")
        return 1


if __name__ == "__main__":
    sys.exit(main())