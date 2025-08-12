#!/usr/bin/env python3
"""Test script to verify hook handler debug mode behavior.

This script tests that debug mode is enabled by default and can be controlled
via the CLAUDE_MPM_HOOK_DEBUG environment variable.
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path so we can import from the project
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def run_hook_handler_test(env_value: str = None, test_name: str = "default") -> Tuple[bool, str, str]:
    """Run the hook handler with specific environment variable and capture output.
    
    Returns: (success, stdout, stderr)
    """
    # Path to hook handler
    hook_handler_path = project_root / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    
    # Set up environment
    env = os.environ.copy()
    if env_value is not None:
        env['CLAUDE_MPM_HOOK_DEBUG'] = env_value
    elif 'CLAUDE_MPM_HOOK_DEBUG' in env:
        # Remove the variable for default test
        del env['CLAUDE_MPM_HOOK_DEBUG']
    
    # Create a simple test event JSON
    test_event = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": f"test_session_{test_name}",
        "prompt": f"Test prompt for {test_name}",
        "cwd": str(project_root)
    }
    
    try:
        # Run the hook handler with the test event
        process = subprocess.run(
            [sys.executable, str(hook_handler_path)],
            input=json.dumps(test_event),
            env=env,
            capture_output=True,
            text=True,
            timeout=10  # 10 second timeout
        )
        
        return process.returncode == 0, process.stdout, process.stderr
        
    except subprocess.TimeoutExpired:
        return False, "", "Process timed out"
    except Exception as e:
        return False, "", str(e)

def analyze_debug_output(stderr: str) -> bool:
    """Analyze stderr to determine if debug output is present."""
    debug_indicators = [
        "Memory hooks not available",
        "Response tracking",
        "✅",
        "❌", 
        "[DEBUG]",
        "Hook handler:",
        "Successfully connected to Socket.IO",
        "Failed to connect to Socket.IO"
    ]
    
    return any(indicator in stderr for indicator in debug_indicators)

def test_debug_mode_scenarios() -> Dict[str, Dict]:
    """Test all debug mode scenarios and return results."""
    
    test_scenarios = [
        # Test default behavior (no environment variable)
        ("default", None, True, "Debug should be enabled by default"),
        
        # Test explicit true values
        ("true_lower", "true", True, "CLAUDE_MPM_HOOK_DEBUG=true should enable debug"),
        ("true_upper", "TRUE", True, "CLAUDE_MPM_HOOK_DEBUG=TRUE should enable debug"),
        ("true_mixed", "True", True, "CLAUDE_MPM_HOOK_DEBUG=True should enable debug"),
        
        # Test explicit false values (should disable debug)
        ("false_lower", "false", False, "CLAUDE_MPM_HOOK_DEBUG=false should disable debug"),
        ("false_upper", "FALSE", False, "CLAUDE_MPM_HOOK_DEBUG=FALSE should disable debug"),
        ("false_mixed", "False", False, "CLAUDE_MPM_HOOK_DEBUG=False should disable debug"),
        
        # Test edge cases (should all enable debug)
        ("empty_string", "", True, "Empty string should enable debug"),
        ("random_value", "random", True, "Random value should enable debug"),
        ("yes", "yes", True, "CLAUDE_MPM_HOOK_DEBUG=yes should enable debug"),
        ("no", "no", True, "CLAUDE_MPM_HOOK_DEBUG=no should enable debug (only 'false' disables)"),
        ("1", "1", True, "CLAUDE_MPM_HOOK_DEBUG=1 should enable debug"),
        ("0", "0", True, "CLAUDE_MPM_HOOK_DEBUG=0 should enable debug (only 'false' disables)"),
        ("disabled", "disabled", True, "CLAUDE_MPM_HOOK_DEBUG=disabled should enable debug"),
    ]
    
    results = {}
    
    print("🧪 Testing Hook Handler Debug Mode Behavior")
    print("=" * 50)
    
    for test_name, env_value, expected_debug, description in test_scenarios:
        print(f"\n📋 Test: {test_name}")
        print(f"   Environment: CLAUDE_MPM_HOOK_DEBUG={repr(env_value)}")
        print(f"   Expected: Debug {'ON' if expected_debug else 'OFF'}")
        print(f"   Description: {description}")
        
        success, stdout, stderr = run_hook_handler_test(env_value, test_name)
        
        if not success:
            print(f"   ❌ FAILED: Hook handler execution failed")
            print(f"      Error: {stderr}")
            results[test_name] = {
                'success': False,
                'expected_debug': expected_debug,
                'actual_debug': None,
                'error': stderr,
                'description': description
            }
            continue
        
        # Check if debug output is present
        actual_debug = analyze_debug_output(stderr)
        
        # Verify the result matches expectation
        test_passed = actual_debug == expected_debug
        
        if test_passed:
            print(f"   ✅ PASSED: Debug is {'ON' if actual_debug else 'OFF'} as expected")
        else:
            print(f"   ❌ FAILED: Debug is {'ON' if actual_debug else 'OFF'}, expected {'ON' if expected_debug else 'OFF'}")
        
        # Show debug output sample if present
        if actual_debug and stderr:
            debug_lines = [line for line in stderr.split('\n') if any(indicator in line for indicator in ['✅', '❌', '[DEBUG]', 'Memory', 'Response'])][:3]
            if debug_lines:
                print(f"   📝 Debug output sample: {debug_lines[0][:80]}...")
        
        results[test_name] = {
            'success': test_passed,
            'expected_debug': expected_debug,
            'actual_debug': actual_debug,
            'stderr_length': len(stderr),
            'stdout': stdout,
            'description': description
        }
    
    return results

def print_summary(results: Dict[str, Dict]):
    """Print test summary."""
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r['success'])
    failed_tests = total_tests - passed_tests
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests > 0:
        print(f"\n❌ FAILED TESTS:")
        for test_name, result in results.items():
            if not result['success']:
                expected = "ON" if result['expected_debug'] else "OFF"
                actual = "ON" if result.get('actual_debug') else "OFF"
                print(f"   • {test_name}: Expected debug {expected}, got {actual}")
                print(f"     {result['description']}")
    
    print(f"\n🎯 KEY FINDINGS:")
    
    # Check default behavior
    default_result = results.get('default', {})
    if default_result.get('success') and default_result.get('actual_debug'):
        print(f"   ✅ Debug is enabled BY DEFAULT (no env var needed)")
    else:
        print(f"   ❌ Debug is NOT enabled by default")
    
    # Check false disabling
    false_tests = [name for name in results if 'false' in name]
    false_working = all(results[name]['success'] for name in false_tests if name in results)
    if false_working:
        print(f"   ✅ Debug can be disabled with CLAUDE_MPM_HOOK_DEBUG=false (case-insensitive)")
    else:
        print(f"   ❌ Debug disabling with 'false' is not working correctly")
    
    # Check backward compatibility
    true_tests = [name for name in results if 'true' in name]
    true_working = all(results[name]['success'] for name in true_tests if name in results)
    if true_working:
        print(f"   ✅ Backward compatible: CLAUDE_MPM_HOOK_DEBUG=true still works")
    else:
        print(f"   ❌ Backward compatibility issue with CLAUDE_MPM_HOOK_DEBUG=true")
    
    # Check edge cases
    edge_cases = ['no', '0', 'disabled', 'random']
    edge_working = all(results[name]['success'] for name in edge_cases if name in results)
    if edge_working:
        print(f"   ✅ Edge cases handled correctly (only 'false' disables debug)")
    else:
        print(f"   ❌ Some edge cases not handled correctly")

def main():
    """Main test execution."""
    print("🔍 Hook Handler Debug Mode Verification")
    print("Testing that debug mode is enabled by default and can be controlled via CLAUDE_MPM_HOOK_DEBUG")
    
    # Run all tests
    results = test_debug_mode_scenarios()
    
    # Print summary
    print_summary(results)
    
    # Return appropriate exit code
    all_passed = all(r['success'] for r in results.values())
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())