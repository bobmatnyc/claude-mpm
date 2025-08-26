"""
Test configuration singleton logging behavior.

Ensures that the configuration loading success message is only logged once,
even when multiple Config instances are created with different parameters.
"""

import logging
import unittest
from io import StringIO


class TestConfigSingletonLogging(unittest.TestCase):
    """Test that configuration loading messages are not duplicated."""

    def setUp(self):
        """Reset singleton before each test."""
        Config.reset_singleton()

    def tearDown(self):
        """Clean up after each test."""
        Config.reset_singleton()

    def test_single_success_message_on_multiple_instances():
        """Test that success message appears only once across multiple Config instances."""
        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)

        # Get the Config logger
        config_logger = logging.getLogger("claude_mpm.core.config")
        config_logger.addHandler(handler)
        config_logger.setLevel(logging.INFO)

        try:
            # Create multiple Config instances
            config1 = Config()
            config2 = Config()
            config3 = Config(config={"test": "value"})

            # Check that all are the same instance
            self.assertIs(config1, config2)
            self.assertIs(config2, config3)

            # Check log output for success message
            log_output = log_capture.getvalue()
            success_count = log_output.count("✓ Successfully loaded configuration")

            # Should appear at most once (might be 0 if no config file exists)
            self.assertLessEqual(
                success_count,
                1,
                f"Success message appeared {success_count} times, expected at most 1",
            )

        finally:
            config_logger.removeHandler(handler)

    def test_no_duplicate_on_explicit_config_file():
        """Test that passing config_file after initialization doesn't duplicate message."""
        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)

        config_logger = logging.getLogger("claude_mpm.core.config")
        config_logger.addHandler(handler)
        config_logger.setLevel(logging.INFO)

        try:
            # Create initial Config
            config1 = Config()

            # Clear the log to isolate the second call
            log_capture.truncate(0)
            log_capture.seek(0)

            # Try to create with explicit config_file
            config2 = Config(config_file=".claude-mpm/configuration.yaml")

            # Should be same instance
            self.assertIs(config1, config2)

            # Check that no new success message was logged
            log_output = log_capture.getvalue()
            success_count = log_output.count("✓ Successfully loaded configuration")

            self.assertEqual(
                success_count,
                0,
                f"Success message appeared {success_count} times after initialization, expected 0",
            )

        finally:
            config_logger.removeHandler(handler)

    def test_debug_message_for_ignored_config_file():
        """Test that debug message is logged when config_file is ignored."""
        # Capture DEBUG log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)

        config_logger = logging.getLogger("claude_mpm.core.config")
        config_logger.addHandler(handler)
        config_logger.setLevel(logging.DEBUG)

        try:
            # Create initial Config
            Config()

            # Clear the log
            log_capture.truncate(0)
            log_capture.seek(0)

            # Try to create with different config_file
            Config(config_file="different.yaml")

            # Check for debug message about ignoring the parameter
            log_output = log_capture.getvalue()
            self.assertIn(
                "Ignoring config_file parameter",
                log_output,
                "Expected debug message about ignoring config_file parameter",
            )

        finally:
            config_logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
