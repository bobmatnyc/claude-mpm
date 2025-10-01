#!/usr/bin/env python3
"""Test script to verify delegation tracking and response logging fixes.

This script tests:
1. PreToolUse properly stores delegation request data with session_id
2. SubagentStop can retrieve the stored data (with fuzzy matching if needed)
3. Response tracking works for delegated tasks
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_delegation_with_response_tracking():
    """Test a delegation to ensure response tracking works."""
    print("\n=== Testing Delegation with Response Tracking ===\n")

    # Enable debug mode and response tracking
    env = os.environ.copy()
    env["CLAUDE_MPM_HOOK_DEBUG"] = "true"
    env["CLAUDE_MPM_RESPONSE_TRACKING"] = "true"
    env["CLAUDE_MPM_RESPONSE_TRACKING_MODE"] = "delegation"

    # Clear any existing response logs
    response_dir = Path.home() / ".claude-mpm" / "responses"
    if response_dir.exists():
        for file in response_dir.glob("*.json"):
            if file.is_file():
                file.unlink()

    # Create a test prompt that will delegate to research agent
    test_prompt = "Use the research agent to analyze the hook_handler.py file structure"

    print(f"Test prompt: {test_prompt}")
    print("\nRunning claude-mpm with delegation...\n")

    # Run claude-mpm with the test prompt
    result = subprocess.run(
        ["./claude-mpm", "run", "-i", test_prompt, "--non-interactive"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    print("=== STDERR Output (Debug Logs) ===")
    print(result.stderr)

    print("\n=== STDOUT Output (Response) ===")
    print(result.stdout[:1000] if len(result.stdout) > 1000 else result.stdout)

    # Check for key indicators in the debug output
    stderr_lines = result.stderr.split("\n")

    # Check for PreToolUse Task delegation tracking
    pre_tool_found = False
    delegation_tracked = False
    subagent_stop_found = False
    response_tracked = False
    session_match = False

    for line in stderr_lines:
        if "[DEBUG] PreToolUse event received:" in line:
            pre_tool_found = True
            print(f"✅ PreToolUse event detected: {line}")

        if "Task delegation tracking:" in line:
            delegation_tracked = True
            print(f"✅ Delegation tracking started: {line}")

        if "✅ Stored in delegation_requests" in line:
            print(f"✅ Delegation stored successfully: {line}")

        if "[DEBUG] SubagentStop event received:" in line:
            subagent_stop_found = True
            print(f"✅ SubagentStop event detected: {line}")

        if "✅ Session found in delegation_requests" in line:
            session_match = True
            print(f"✅ Session matched successfully: {line}")

        if "✅ Fuzzy match found:" in line:
            session_match = True
            print(f"✅ Fuzzy match worked: {line}")

        if "✅ Found request data for response tracking" in line:
            response_tracked = True
            print(f"✅ Response tracking data found: {line}")

        if "❌ Session NOT found in delegation_requests!" in line:
            print(f"❌ Session mismatch detected: {line}")

        if "❌ No request data found for session" in line:
            print(f"❌ No request data found: {line}")

    # Check if response files were created
    print("\n=== Checking Response Files ===")
    response_files = list(response_dir.glob("*.json")) if response_dir.exists() else []

    if response_files:
        print(f"✅ Found {len(response_files)} response file(s)")
        for file in response_files[:3]:  # Show first 3
            print(f"  - {file.name}")
            # Read and show a snippet of the response
            with file.open() as f:
                data = json.load(f)
                agent_type = data.get("agent_type", "unknown")
                request_preview = data.get("request", "")[:100]
                print(f"    Agent: {agent_type}")
                print(f"    Request: {request_preview}...")
    else:
        print("❌ No response files found")

    # Summary
    print("\n=== Test Summary ===")

    tests_passed = 0
    tests_total = 6

    if pre_tool_found:
        print("✅ PreToolUse event handling: PASS")
        tests_passed += 1
    else:
        print("❌ PreToolUse event handling: FAIL")

    if delegation_tracked:
        print("✅ Delegation tracking: PASS")
        tests_passed += 1
    else:
        print("❌ Delegation tracking: FAIL")

    if subagent_stop_found:
        print("✅ SubagentStop event handling: PASS")
        tests_passed += 1
    else:
        print("❌ SubagentStop event handling: FAIL")

    if session_match:
        print("✅ Session correlation: PASS")
        tests_passed += 1
    else:
        print("❌ Session correlation: FAIL")

    if response_tracked:
        print("✅ Response data retrieval: PASS")
        tests_passed += 1
    else:
        print("❌ Response data retrieval: FAIL")

    if response_files:
        print("✅ Response file creation: PASS")
        tests_passed += 1
    else:
        print("❌ Response file creation: FAIL")

    print(f"\nResult: {tests_passed}/{tests_total} tests passed")

    if tests_passed == tests_total:
        print("\n🎉 All tests passed! Delegation tracking is working correctly.")
        return 0
    print(
        f"\n⚠️ {tests_total - tests_passed} test(s) failed. Check the debug output above."
    )
    return 1


def main():
    """Main entry point."""
    print("=== Delegation Tracking Fix Test ===")
    print(
        "This script tests the fix for SubagentStop events not finding stored request data."
    )

    try:
        exit_code = test_delegation_with_response_tracking()
        sys.exit(exit_code)
    except subprocess.TimeoutExpired:
        print("\n❌ Test timed out after 60 seconds")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
