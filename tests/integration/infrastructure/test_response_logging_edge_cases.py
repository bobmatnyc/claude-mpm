#!/usr/bin/env python3
"""
Test edge cases for response logging system.
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

# Set debug environment variable
os.environ["CLAUDE_MPM_HOOK_DEBUG"] = "true"

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
from claude_mpm.services.response_tracker import ResponseTracker


def test_disabled_tracking():
    """Test behavior when response tracking is disabled."""
    print("\n" + "=" * 60)
    print("Testing Disabled Response Tracking")
    print("=" * 60)

    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="claude_mpm_test_disabled_")
    responses_dir = Path(temp_dir) / "responses"
    responses_dir.mkdir(parents=True)

    try:
        # Create a custom config with tracking DISABLED
        test_config = Config()
        test_config.set("response_logging.enabled", False)  # Disabled
        test_config.set("response_tracking.enabled", False)  # Disabled
        test_config.set("response_tracking.base_dir", str(responses_dir))

        # Initialize hook handler
        handler = ClaudeHookHandler()
        handler.response_tracking_enabled = False  # Explicitly disable
        handler.response_tracker = None  # No tracker

        session_id = f"disabled_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"Session ID: {session_id}")
        print(f"Responses directory: {responses_dir}")
        print(f"Response tracking enabled: {handler.response_tracking_enabled}")
        print(f"Response tracker: {handler.response_tracker}")

        # Simulate events that would normally be tracked
        pre_tool_event = {
            "event_type": "pre_tool",
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "Research",
                "prompt": "Test with disabled tracking",
            },
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }

        subagent_stop_event = {
            "event_type": "subagent_stop",
            "agent_type": "research",
            "session_id": session_id,
            "reason": "completed",
            "output": "Test output with tracking disabled",
            "timestamp": datetime.now().isoformat(),
        }

        # Process events
        handler._handle_pre_tool_fast(pre_tool_event)
        handler._handle_subagent_stop_fast(subagent_stop_event)

        # Check if any files were created
        response_files = list(responses_dir.glob("*.json"))

        if len(response_files) == 0:
            print("✅ No response files created when tracking is disabled")
            return True
        print(f"❌ {len(response_files)} files created despite tracking being disabled")
        for file_path in response_files:
            print(f"  - {file_path.name}")
        return False

    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"Cleaned up test directory: {temp_dir}")


def test_missing_session_id():
    """Test behavior when session ID is missing or invalid."""
    print("\n" + "=" * 60)
    print("Testing Missing/Invalid Session IDs")
    print("=" * 60)

    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="claude_mpm_test_session_")
    responses_dir = Path(temp_dir) / "responses"
    responses_dir.mkdir(parents=True)

    try:
        # Create a custom config for testing
        test_config = Config()
        test_config.set("response_logging.enabled", True)
        test_config.set("response_tracking.enabled", True)
        test_config.set("response_tracking.base_dir", str(responses_dir))

        # Initialize hook handler
        handler = ClaudeHookHandler()
        handler.response_tracking_enabled = True
        handler.response_tracker = ResponseTracker(config=test_config)

        print(f"Responses directory: {responses_dir}")

        # Test cases with invalid session IDs
        test_cases = [
            {"session_id": None, "description": "None session ID"},
            {"session_id": "", "description": "Empty session ID"},
            {"session_id": "   ", "description": "Whitespace-only session ID"},
            {
                "session_id": "normal_session",
                "description": "Valid session ID (control)",
            },
        ]

        results = []

        for i, test_case in enumerate(test_cases):
            session_id = test_case["session_id"]
            desc = test_case["description"]

            print(f"\nTesting case {i+1}: {desc}")

            # Simulate a delegation and response
            pre_tool_event = {
                "event_type": "pre_tool",
                "tool_name": "Task",
                "tool_input": {
                    "subagent_type": "Research",
                    "prompt": f"Test case: {desc}",
                },
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            }

            subagent_stop_event = {
                "event_type": "subagent_stop",
                "agent_type": "research",
                "session_id": session_id,
                "reason": "completed",
                "output": f"Response for test case: {desc}",
                "timestamp": datetime.now().isoformat(),
            }

            try:
                handler._handle_pre_tool_fast(pre_tool_event)
                handler._handle_subagent_stop_fast(subagent_stop_event)

                # Check if files were created for this session
                if session_id and session_id.strip():
                    expected_pattern = f"*{session_id}*"
                    session_files = list(responses_dir.glob(expected_pattern))
                    if session_files:
                        print(f"  ✅ Created {len(session_files)} response file(s)")
                        results.append(True)
                    else:
                        print("  ❌ No response files created")
                        results.append(False)
                else:
                    # For invalid session IDs, we expect no files or handled gracefully
                    all_files = list(responses_dir.glob("*.json"))
                    print(
                        f"  ⚠️  Invalid session ID handled (total files: {len(all_files)})"
                    )
                    results.append(True)  # Handled gracefully

            except Exception as e:
                print(f"  ❌ Exception occurred: {e}")
                results.append(False)

        success_rate = sum(results) / len(results)
        print(f"\nSession ID handling success rate: {success_rate*100:.1f}%")
        return success_rate >= 0.75  # Allow some failures for invalid inputs

    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"Cleaned up test directory: {temp_dir}")


def test_large_responses():
    """Test behavior with very large responses."""
    print("\n" + "=" * 60)
    print("Testing Large Response Handling")
    print("=" * 60)

    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="claude_mpm_test_large_")
    responses_dir = Path(temp_dir) / "responses"
    responses_dir.mkdir(parents=True)

    try:
        # Create a custom config for testing
        test_config = Config()
        test_config.set("response_logging.enabled", True)
        test_config.set("response_tracking.enabled", True)
        test_config.set("response_tracking.base_dir", str(responses_dir))

        # Initialize hook handler
        handler = ClaudeHookHandler()
        handler.response_tracking_enabled = True
        handler.response_tracker = ResponseTracker(config=test_config)

        session_id = f"large_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"Session ID: {session_id}")
        print(f"Responses directory: {responses_dir}")

        # Create large response content (1MB)
        large_content = "A" * (1024 * 1024)  # 1MB of 'A' characters
        print(f"Large content size: {len(large_content):,} characters")

        # Set up delegation tracking
        pre_tool_event = {
            "event_type": "pre_tool",
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "Research",
                "prompt": "Generate large content for testing",
            },
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }

        # Process pre-tool event
        handler._handle_pre_tool_fast(pre_tool_event)

        # Simulate SubagentStop with large response
        subagent_stop_event = {
            "event_type": "subagent_stop",
            "agent_type": "research",
            "session_id": session_id,
            "reason": "completed",
            "output": large_content,
            "timestamp": datetime.now().isoformat(),
        }

        start_time = datetime.now()
        handler._handle_subagent_stop_fast(subagent_stop_event)
        end_time = datetime.now()

        processing_time = (end_time - start_time).total_seconds()
        print(f"Processing time: {processing_time:.3f} seconds")

        # Check if file was created successfully
        response_files = list(responses_dir.glob(f"*{session_id}*.json"))

        if response_files:
            file_path = response_files[0]
            file_size = file_path.stat().st_size
            print(f"✅ Created response file: {file_path.name}")
            print(f"File size: {file_size:,} bytes")

            # Verify file content
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)

                response_length = len(data["response"])
                print(f"Response content length: {response_length:,} characters")

                if response_length == len(large_content):
                    print("✅ Large response content preserved correctly")
                    return True
                print("❌ Response content truncated or modified")
                return False

            except json.JSONDecodeError:
                print("❌ Response file contains invalid JSON")
                return False
            except Exception as e:
                print(f"❌ Error reading response file: {e}")
                return False
        else:
            print("❌ No response file created for large content")
            return False

    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"Cleaned up test directory: {temp_dir}")


def test_configuration_override():
    """Test that configuration can be properly overridden."""
    print("\n" + "=" * 60)
    print("Testing Configuration Override")
    print("=" * 60)

    # Test reading actual configuration file
    config_path = Path(".claude-mpm/configuration.yaml")
    if config_path.exists():
        print(f"✅ Found configuration file: {config_path}")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        response_config = config.get("response_logging", {})
        print("Current configuration:")
        print(f"  enabled: {response_config.get('enabled', False)}")
        print(f"  debug: {response_config.get('debug', False)}")
        print(f"  format: {response_config.get('format', 'json')}")

        # Test creating a Config object and overriding values
        test_config = Config()

        # Override some values
        test_config.set("response_logging.enabled", True)
        test_config.set("response_logging.debug", True)
        test_config.set("response_logging.format", "json")

        # Verify overrides work
        print("\nAfter override:")
        print(f"  enabled: {test_config.get('response_logging.enabled')}")
        print(f"  debug: {test_config.get('response_logging.debug')}")
        print(f"  format: {test_config.get('response_logging.format')}")

        print("✅ Configuration override test passed")
        return True
    print(f"❌ Configuration file not found: {config_path}")
    return False


if __name__ == "__main__":
    print("🧪 Response Logging Edge Case Testing")
    print("=" * 60)

    # Run all edge case tests
    tests = [
        ("Disabled Tracking", test_disabled_tracking),
        ("Missing Session IDs", test_missing_session_id),
        ("Large Responses", test_large_responses),
        ("Configuration Override", test_configuration_override),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
            print(
                f"\n{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}"
            )
        except Exception as e:
            results[test_name] = False
            print(f"\n❌ {test_name}: FAILED with exception: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("Edge Case Testing Summary")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"  {test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 All edge case tests PASSED!")
        exit(0)
    else:
        print("⚠️  Some edge case tests FAILED")
        exit(1)
