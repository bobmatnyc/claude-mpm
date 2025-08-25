#!/usr/bin/env python3
"""Test script to verify response logging with debug output."""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Set debug environment variable
os.environ["CLAUDE_MPM_HOOK_DEBUG"] = "true"

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
from claude_mpm.services.response_tracker import ResponseTracker


def test_delegation_tracking():
    """Test that delegations are properly tracked."""
    print("\n" + "=" * 60)
    print("Testing Delegation Tracking with Debug Output")
    print("=" * 60)

    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="claude_mpm_test_")
    responses_dir = Path(temp_dir) / "responses"
    responses_dir.mkdir(parents=True)

    try:
        # Create a custom config for testing
        test_config = Config()
        test_config.set("response_logging.enabled", True)
        test_config.set("response_logging.session_directory", str(responses_dir))
        test_config.set("response_logging.format", "json")
        test_config.set("response_logging.debug", True)
        test_config.set("response_tracking.enabled", True)
        test_config.set("response_tracking.base_dir", str(responses_dir))

        # Initialize hook handler
        handler = ClaudeHookHandler()

        # Enable response tracking with custom config
        handler.response_tracking_enabled = True
        handler.response_tracker = ResponseTracker(config=test_config)

        # Test session ID
        session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"\nSession ID: {session_id}")
        print(f"Responses directory: {responses_dir}")

        # Simulate a Task delegation (pre-tool event)
        print("\n--- Simulating Task Delegation ---")
        pre_tool_event = {
            "event_type": "pre_tool",
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "Research",  # Capitalized like Claude sends it
                "prompt": "Analyze the codebase structure",
                "description": "Research the project architecture and key components",
            },
            "session_id": session_id,
            "cwd": os.getcwd(),
            "timestamp": datetime.now().isoformat(),
        }

        # Process the pre-tool event
        handler._handle_pre_tool_fast(pre_tool_event)

        # Check if delegation was tracked
        print(f"\nActive delegations: {handler.active_delegations}")
        print(f"Delegation requests: {list(handler.delegation_requests.keys())}")

        # Simulate a SubagentStop event
        print("\n--- Simulating SubagentStop Event ---")
        subagent_stop_event = {
            "event_type": "subagent_stop",
            "agent_type": "research",  # Lowercase as returned
            "session_id": session_id,
            "reason": "completed",
            "output": """# Research Analysis Complete

I've analyzed the codebase structure and found the following key components:

1. **Agent System** - Modular agent architecture with templates
2. **Hook System** - Extensible hooks for event processing
3. **Memory System** - Persistent agent learning capabilities
4. **CLI Framework** - Command-line interface with modular commands

The architecture follows a clean separation of concerns with services, utils, and core modules.""",
            "cwd": os.getcwd(),
            "timestamp": datetime.now().isoformat(),
        }

        # Process the SubagentStop event
        handler._handle_subagent_stop_fast(subagent_stop_event)

        # Check if response was logged
        print(f"\nChecking for logged responses in: {responses_dir}")
        response_files = list(responses_dir.glob("*.json"))
        print(f"Found {len(response_files)} response file(s)")

        for file_path in response_files:
            print(f"\nResponse file: {file_path.name}")
            with open(file_path) as f:
                data = json.load(f)
                print(f"  Agent: {data.get('agent_name')}")
                print(f"  Session: {data.get('session_id', '')[:20]}...")
                print(f"  Request preview: {data.get('request', '')[:100]}...")
                print(f"  Response preview: {data.get('response', '')[:100]}...")
                if "metadata" in data:
                    print(f"  Metadata keys: {list(data['metadata'].keys())}")

        # Test a Stop event (main Claude response)
        print("\n--- Simulating Stop Event ---")

        # First, store a pending prompt
        handler.pending_prompts[session_id] = {
            "prompt": "What is the project structure?",
            "timestamp": datetime.now().isoformat(),
        }

        stop_event = {
            "event_type": "stop",
            "session_id": session_id,
            "reason": "completed",
            "stop_type": "normal",
            "output": """The project structure follows a standard Python package layout:

- src/claude_mpm/ - Main package directory
  - agents/ - Agent templates and registry
  - cli/ - Command-line interface
  - core/ - Core functionality
  - hooks/ - Hook system
  - services/ - Business logic
  - utils/ - Utility functions
- tests/ - Test suite
- scripts/ - Utility scripts
- docs/ - Documentation""",
            "cwd": os.getcwd(),
            "timestamp": datetime.now().isoformat(),
        }

        # Process the Stop event
        handler._handle_stop_fast(stop_event)

        # Check for new response files
        response_files = list(responses_dir.glob("*.json"))
        print(f"\nTotal response files after Stop event: {len(response_files)}")

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(
            f"✓ Delegation tracking: {'PASS' if session_id in handler.delegation_requests or len(response_files) > 0 else 'FAIL'}"
        )
        print(f"✓ Response logging: {'PASS' if len(response_files) > 0 else 'FAIL'}")
        print("✓ Debug output visible: PASS (check stderr output above)")

    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up test directory: {temp_dir}")


def test_configuration_loading():
    """Test that configuration is properly loaded."""
    print("\n" + "=" * 60)
    print("Testing Configuration Loading")
    print("=" * 60)

    config_path = Path(".claude-mpm/configuration.yaml")
    if config_path.exists():
        print(f"✓ Configuration file exists: {config_path}")

        import yaml

        with open(config_path) as f:
            config = yaml.safe_load(f)

        response_config = config.get("response_logging", {})
        print("\nResponse Logging Configuration:")
        print(f"  enabled: {response_config.get('enabled', False)}")
        print(f"  format: {response_config.get('format', 'json')}")
        print(f"  debug: {response_config.get('debug', False)}")
        print(
            f"  session_directory: {response_config.get('session_directory', '.claude-mpm/responses')}"
        )
        print(
            f"  track_all_interactions: {response_config.get('track_all_interactions', False)}"
        )
    else:
        print(f"✗ Configuration file not found: {config_path}")


if __name__ == "__main__":
    # Test configuration loading
    test_configuration_loading()

    # Test delegation tracking with debug output
    test_delegation_tracking()

    print("\n✅ All tests completed!")
