#!/usr/bin/env python
"""
Integration test for response logging in interactive sessions.

WHY: This test verifies the complete flow of response logging in interactive
sessions, from initialization through cleanup, including the singleton pattern
that allows the hook handler and InteractiveSession to share the same logger.

DESIGN DECISION: We test the actual flow rather than mocking components to
ensure that the response logging works correctly when all parts are integrated.
"""

import json
import os
import shutil
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_interactive_response_logging_integration():
    """Test that interactive sessions properly log responses when enabled."""

    # Create temporary directory for test
    temp_dir = tmp_path
    response_dir = Path(temp_dir) / "responses"

    try:
        # Create config file with response logging enabled
        config_file = Path(temp_dir) / "config.json"
        config_data = {
            "response_logging": {
                "enabled": True,
                "session_directory": str(response_dir),
                "format": "json",
            }
        }

        with config_file.open("w") as f:
            json.dump(config_data, f)

        # Initialize components
        from claude_mpm.core.claude_runner import ClaudeRunner
        from claude_mpm.core.interactive_session import InteractiveSession
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        # Create config
        config = Config(config_file=str(config_file))

        # Create ClaudeRunner
        runner = ClaudeRunner()

        # Override the config with our test config
        runner.config = config

        # Create InteractiveSession
        session = InteractiveSession(runner)

        # Initialize session
        success, error = session.initialize_interactive_session()
        assert success, f"Failed to initialize session: {error}"

        # Verify response tracker was initialized
        assert session.response_tracker is not None, "Response tracker not initialized"
        assert session.response_tracker.enabled, "Response tracker not enabled"

        # Verify session ID was set
        assert session.session_id is not None, "Session ID not generated"
        assert (
            session.response_tracker.session_logger.session_id == session.session_id
        ), "Session ID not set in logger"

        # Create hook handler (simulating Claude's hook system)
        hook_handler = ClaudeHookHandler()

        # Verify both use the same session logger (singleton pattern)
        if hook_handler.response_tracker and session.response_tracker:
            assert (
                hook_handler.response_tracker.session_logger
                is session.response_tracker.session_logger
            ), "Hook handler and session not sharing same logger instance"

        # Simulate a response being tracked
        if session.response_tracker.enabled:
            file_path = session.response_tracker.track_response(
                agent_name="test_agent",
                request="Test request",
                response="Test response",
                session_id=session.session_id,
                metadata={"test": True},
            )

            # Verify file was created (or async logging is being used)
            if file_path:
                # Check if file exists or if async logging is being used
                if file_path.name == "async_response.json":
                    # Async logging - file will be created asynchronously
                    print("✓ Async response logging initiated")
                else:
                    # Synchronous logging - file should exist immediately
                    assert file_path.exists(), (
                        f"Response file not created at {file_path}"
                    )

                    # Verify content
                    with file_path.open() as f:
                        content = json.load(f)
                        assert content["request"] == "Test request"
                        assert content["response"] == "Test response"
                        assert content["agent_name"] == "test_agent"
                        assert content["session_id"] == session.session_id

        # Clean up session
        session.cleanup_interactive_session()

        # Verify session ID was cleared
        assert session.response_tracker.session_logger.session_id is None, (
            "Session ID not cleared after cleanup"
        )

        print("✅ Interactive response logging integration test passed!")

    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_response_logging_disabled():
    """Test that response logging doesn't interfere when disabled."""

    # Create temporary directory for test
    temp_dir = tmp_path

    try:
        # Create config file with response logging disabled
        config_file = Path(temp_dir) / "config.json"
        config_data = {"response_logging": {"enabled": False}}

        with config_file.open("w") as f:
            json.dump(config_data, f)

        # Initialize components
        from claude_mpm.core.claude_runner import ClaudeRunner
        from claude_mpm.core.interactive_session import InteractiveSession

        # Create config
        config = Config(config_file=str(config_file))

        # Create ClaudeRunner
        runner = ClaudeRunner()

        # Override the config with our test config
        runner.config = config

        # Create InteractiveSession
        session = InteractiveSession(runner)

        # Initialize session
        success, error = session.initialize_interactive_session()
        assert success, f"Failed to initialize session: {error}"

        # Verify response tracker was not enabled
        if session.response_tracker:
            assert not session.response_tracker.enabled, (
                "Response tracker should be disabled"
            )

        # Clean up session - should not raise any errors
        session.cleanup_interactive_session()

        print("✅ Response logging disabled test passed!")

    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_interactive_response_logging_integration()
    test_response_logging_disabled()
    print("\n✅ All integration tests passed!")
