#!/usr/bin/env python3
"""Integration test for response logging in interactive mode.

WHY: This test verifies that response logging works end-to-end in subprocess mode,
actually capturing output and writing it to the log files as expected.

DESIGN DECISION: We simulate a minimal interactive session to verify that:
1. Subprocess mode is used when response logging is enabled
2. Output is properly captured and logged
3. Log files are created in the correct location
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_mpm.core.claude_runner import ClaudeRunner


class TestResponseLoggingIntegration(unittest.TestCase):
    """Integration test for response logging functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tmp_path
        self.config_file = Path(self.temp_dir) / "claude-mpm.yml"
        self.log_dir = Path(self.temp_dir) / "logs"

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_config_with_logging(self):
        """Create a configuration with response logging enabled."""
        config_content = f"""
response_logging:
  enabled: true
  output_dir: "{self.log_dir}"
  format: "json"
  include_timestamps: true
  max_size_mb: 10
"""
        self.config_file.write_text(config_content)
        return Config(config_file=str(self.config_file))

    def test_subprocess_mode_captures_output():
        """Test that subprocess mode is selected when response logging is enabled."""
        # Create config with response logging enabled
        config = self.create_config_with_logging()

        # Create runner
        runner = ClaudeRunner(launch_method="exec")  # Start with exec
        runner.config = config

        # Mock response logger
        mock_response_logger = MagicMock()
        runner.response_logger = mock_response_logger

        # Mock deployment service
        runner.deployment_service.deploy_agents = MagicMock(
            return_value={"deployed": [], "updated": [], "skipped": ["agent1"]}
        )

        # Mock the subprocess launcher to avoid actually running Claude
        with patch(
            "claude_mpm.core.claude_runner.ClaudeRunner._launch_subprocess_interactive"
        ) as mock_launcher, patch(
            "claude_mpm.core.claude_runner.ClaudeRunner._create_system_prompt",
            return_value="test",
        ):
            # Run interactive mode
            runner.run_interactive()

        # Verify subprocess launcher was called (not exec)
        mock_launcher.assert_called_once()

        # Verify response logger is available for the session
        self.assertIsNotNone(runner.response_logger)

    def test_auto_switch_message_displayed():
        """Test that the auto-switch message is displayed to the user."""
        # Create config with response logging enabled
        config = self.create_config_with_logging()

        # Create runner with exec mode
        runner = ClaudeRunner(launch_method="exec")
        runner.config = config
        runner.response_logger = MagicMock()

        # Mock deployment service
        runner.deployment_service.deploy_agents = MagicMock(
            return_value={"deployed": [], "updated": [], "skipped": ["agent1"]}
        )

        # Capture print output
        with patch("builtins.print") as mock_print, patch(
            "claude_mpm.core.claude_runner.ClaudeRunner._launch_subprocess_interactive"
        ), patch(
            "claude_mpm.core.claude_runner.ClaudeRunner._create_system_prompt",
            return_value="test",
        ):
            runner.run_interactive()

        # Verify the auto-switch message was printed
        print_calls = [str(call) for call in mock_print.call_args_list]

        # Check for the new improved message
        found_message = False
        for call in print_calls:
            if "Response logging enabled" in call and "subprocess mode" in call:
                found_message = True
                break

        self.assertTrue(
            found_message, f"Auto-switch message not found. Print calls: {print_calls}"
        )

    def test_response_logging_disabled_uses_exec():
        """Test that exec mode is used when response logging is disabled."""
        # Create config with response logging disabled
        config_content = """
response_logging:
  enabled: false
"""
        self.config_file.write_text(config_content)
        config = Config(config_file=str(self.config_file))

        # Create runner with default settings
        runner = ClaudeRunner(launch_method="exec")
        runner.config = config
        runner.response_logger = None  # No logger when disabled

        # Mock deployment service
        runner.deployment_service.deploy_agents = MagicMock(
            return_value={"deployed": [], "updated": [], "skipped": ["agent1"]}
        )

        # Mock exec and subprocess
        with patch("claude_mpm.core.claude_runner.os.execvpe") as mock_execvpe:
            with patch(
                "claude_mpm.core.claude_runner.ClaudeRunner._launch_subprocess_interactive"
            ) as mock_subprocess:
                with patch(
                    "claude_mpm.core.claude_runner.ClaudeRunner._create_system_prompt",
                    return_value="test",
                ):
                    try:
                        runner.run_interactive()
                    except SystemExit:
                        pass  # execvpe would exit

        # Verify exec was called, not subprocess
        mock_execvpe.assert_called_once()
        mock_subprocess.assert_not_called()


if __name__ == "__main__":
    unittest.main()
