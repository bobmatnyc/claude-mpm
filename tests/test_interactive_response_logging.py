#!/usr/bin/env python
"""
Test response logging for interactive sessions.

WHY: This test verifies that interactive sessions properly initialize response
tracking when enabled in configuration, ensuring that Claude's responses are
logged during interactive sessions just like they are in oneshot mode.

DESIGN DECISION: We test both the initialization of response tracking and its
integration with the hook system, verifying that the singleton pattern allows
proper sharing of the session logger between components.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from claude_mpm.core.claude_runner import ClaudeRunner
from claude_mpm.core.interactive_session import InteractiveSession


class TestInteractiveResponseLogging(unittest.TestCase):
    """Test response logging functionality in interactive sessions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tmp_path
        self.config_path = Path(self.temp_dir) / "config.json"

        # Create config with response logging enabled
        self.config_data = {
            "response_logging": {
                "enabled": True,
                "session_directory": str(Path(self.temp_dir) / "responses"),
                "format": "json",
            }
        }

        with self.config_path.open("w") as f:
            json.dump(self.config_data, f)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_response_tracker_initialized_when_enabled():
        """Test that response tracker is initialized when response logging is enabled."""
        # Create mock runner with config
        mock_runner = Mock(spec=ClaudeRunner)
        mock_runner.config = Config(config_file=str(self.config_path))
        mock_runner.project_logger = None
        mock_runner.enable_websocket = False
        mock_runner._get_version = Mock(return_value="3.8.0")

        # Create interactive session
        session = InteractiveSession(mock_runner)

        # Verify response tracker was initialized
        self.assertIsNotNone(session.response_tracker)
        self.assertTrue(session.response_tracker.enabled)
        self.assertIsNotNone(session.response_tracker.session_logger)

    def test_response_tracker_not_initialized_when_disabled():
        """Test that response tracker is not initialized when response logging is disabled."""
        # Update config to disable response logging
        self.config_data["response_logging"]["enabled"] = False
        with self.config_path.open("w") as f:
            json.dump(self.config_data, f)

        # Create mock runner with config
        mock_runner = Mock(spec=ClaudeRunner)
        mock_runner.config = Config(config_file=str(self.config_path))
        mock_runner.project_logger = None
        mock_runner.enable_websocket = False
        mock_runner._get_version = Mock(return_value="3.8.0")

        # Create interactive session
        session = InteractiveSession(mock_runner)

        # Verify response tracker was not initialized (or is disabled)
        if session.response_tracker:
            self.assertFalse(session.response_tracker.enabled)

    def test_session_id_set_in_tracker():
        """Test that session ID is properly set in the response tracker."""
        # Create mock runner with config
        mock_runner = Mock(spec=ClaudeRunner)
        mock_runner.config = Config(config_file=str(self.config_path))
        mock_runner.project_logger = None
        mock_runner.enable_websocket = False
        mock_runner._get_version = Mock(return_value="3.8.0")

        # Create interactive session
        session = InteractiveSession(mock_runner)

        # Initialize the session
        success, error = session.initialize_interactive_session()

        # Verify session was initialized successfully
        self.assertTrue(success)
        self.assertIsNone(error)

        # Verify session ID was generated
        self.assertIsNotNone(session.session_id)

        # Verify session ID was set in tracker if enabled
        if (
            session.response_tracker
            and session.response_tracker.enabled
            and (
                hasattr(session.response_tracker, "session_logger")
                and session.response_tracker.session_logger
            )
        ):
            self.assertEqual(
                session.response_tracker.session_logger.session_id,
                session.session_id,
            )

    def test_cleanup_clears_session_id():
        """Test that cleanup properly clears the session ID from the tracker."""
        # Create mock runner with config
        mock_runner = Mock(spec=ClaudeRunner)
        mock_runner.config = Config(config_file=str(self.config_path))
        mock_runner.project_logger = None
        mock_runner.enable_websocket = False
        mock_runner._get_version = Mock(return_value="3.8.0")
        mock_runner.websocket_server = None
        mock_runner.session_log_file = None

        # Create interactive session
        session = InteractiveSession(mock_runner)

        # Initialize the session
        session.initialize_interactive_session()

        # Store the session ID
        session_id = session.session_id

        # Verify session ID is set
        if (
            session.response_tracker
            and session.response_tracker.enabled
            and (
                hasattr(session.response_tracker, "session_logger")
                and session.response_tracker.session_logger
            )
        ):
            self.assertEqual(
                session.response_tracker.session_logger.session_id, session_id
            )

        # Clean up the session
        session.cleanup_interactive_session()

        # Verify session ID was cleared
        if (
            session.response_tracker
            and session.response_tracker.enabled
            and (
                hasattr(session.response_tracker, "session_logger")
                and session.response_tracker.session_logger
            )
        ):
            self.assertIsNone(session.response_tracker.session_logger.session_id)

    @patch("claude_mpm.services.response_tracker.ResponseTracker")
    def test_response_tracker_initialization_failure_handled(self):
        """Test that failure to initialize response tracker is handled gracefully."""
        # Make ResponseTracker initialization fail
        self.side_effect = Exception("Test error")

        # Create mock runner with config
        mock_runner = Mock(spec=ClaudeRunner)
        mock_runner.config = Config(config_file=str(self.config_path))
        mock_runner.project_logger = None
        mock_runner.enable_websocket = False
        mock_runner._get_version = Mock(return_value="3.8.0")

        # Create interactive session - should not raise
        session = InteractiveSession(mock_runner)

        # Verify session was created despite tracker failure
        self.assertIsNotNone(session)
        # Tracker should be None since initialization failed
        self.assertIsNone(session.response_tracker)

    def test_singleton_pattern_sharing():
        """Test that multiple ResponseTracker instances share the same session logger."""
        from claude_mpm.services.claude_session_logger import get_session_logger
        from claude_mpm.services.response_tracker import ResponseTracker

        # Create config
        config = Config(config_file=str(self.config_path))

        # Create first tracker
        tracker1 = ResponseTracker(config)

        # Create second tracker
        tracker2 = ResponseTracker(config)

        # Get the singleton session logger
        singleton_logger = get_session_logger(config)

        # Verify all three share the same session logger instance
        if tracker1.enabled and tracker2.enabled:
            self.assertIs(tracker1.session_logger, tracker2.session_logger)
            self.assertIs(tracker1.session_logger, singleton_logger)


if __name__ == "__main__":
    unittest.main()
