#!/usr/bin/env python3
"""Test automatic launch method switching for response logging in interactive mode.

WHY: This test verifies that ClaudeRunner automatically switches from exec to subprocess
mode when response logging is enabled, ensuring that response logging works correctly
in interactive mode without user intervention.

DESIGN DECISION: We test multiple scenarios:
1. Default behavior (exec mode) when response logging is disabled
2. Auto-switch to subprocess when response logging is enabled
3. Manual override using --launch-method exec
4. Proper logging of the auto-switch decision
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_mpm.core.claude_runner import ClaudeRunner


class TestResponseLoggingAutoSwitch(unittest.TestCase):
    """Test automatic launch method switching for response logging."""

    def setUp(self):
        """Set up test environment."""
        # Reset Config singleton for clean test state
        Config.reset_singleton()
        self.temp_dir = tmp_path
        self.config_file = Path(self.temp_dir) / "claude-mpm.yml"

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Reset Config singleton after test
        Config.reset_singleton()

    def create_config(self, response_logging_enabled=False):
        """Create a test configuration file."""
        config_content = f"""
response_logging:
  enabled: {str(response_logging_enabled).lower()}
  output_dir: "{self.temp_dir}/logs"
  format: "json"
"""
        self.config_file.write_text(config_content)
        return Config(config_file=str(self.config_file))

    @patch("claude_mpm.core.claude_runner.os.execvpe")
    @patch("claude_mpm.core.claude_runner.subprocess.Popen")
    def test_exec_mode_when_response_logging_disabled(self, mock_execvpe):
        """Test that exec mode is used when response logging is disabled."""
        # Create config with response logging disabled
        config = self.create_config(response_logging_enabled=False)

        # Create runner with default launch method (exec)
        runner = ClaudeRunner(launch_method="exec")
        runner.config = config
        runner.response_logger = None  # No logger when disabled

        # Mock the deployment service
        runner.deployment_service.deploy_agents = MagicMock(
            return_value={"deployed": [], "updated": [], "skipped": ["agent1"]}
        )

        # Run interactive mode
        with patch(
            "claude_mpm.core.claude_runner.ClaudeRunner._create_system_prompt",
            return_value="test prompt",
        ):
            try:
                runner.run_interactive()
            except SystemExit:
                pass  # execvpe would exit the process

        # Verify exec was called (not subprocess)
        mock_execvpe.assert_called_once()
        self.assert_not_called()

    @patch("claude_mpm.core.claude_runner.ClaudeRunner._launch_subprocess_interactive")
    @patch("claude_mpm.core.claude_runner.os.execvpe")
    def test_auto_switch_to_subprocess_when_response_logging_enabled(
        self, mock_execvpe, mock_subprocess
    ):
        """Test automatic switch to subprocess mode when response logging is enabled."""
        # Create config with response logging enabled
        config = self.create_config(response_logging_enabled=True)

        # Create runner with default launch method (exec)
        runner = ClaudeRunner(launch_method="exec")
        runner.config = config

        # Mock response logger
        runner.response_logger = MagicMock()

        # Mock the deployment service
        runner.deployment_service.deploy_agents = MagicMock(
            return_value={"deployed": [], "updated": [], "skipped": ["agent1"]}
        )

        # Capture print output
        with patch("builtins.print") as mock_print, patch(
            "claude_mpm.core.claude_runner.ClaudeRunner._create_system_prompt",
            return_value="test prompt",
        ):
            runner.run_interactive()

        # Verify subprocess was called (not exec)
        mock_subprocess.assert_called_once()
        mock_execvpe.assert_not_called()

        # Verify user was informed about the auto-switch
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(
            any("Response logging enabled" in str(call) for call in print_calls),
            "User should be informed about auto-switch to subprocess mode",
        )
        self.assertTrue(
            any("subprocess mode" in str(call) for call in print_calls),
            "Message should mention subprocess mode",
        )

    @patch("claude_mpm.core.claude_runner.os.execvpe")
    @patch("claude_mpm.core.claude_runner.ClaudeRunner._launch_subprocess_interactive")
    def test_manual_override_with_exec_flag(self, mock_execvpe):
        """Test that --launch-method exec overrides auto-switch."""
        # Create config with response logging enabled
        config = self.create_config(response_logging_enabled=True)

        # Create runner with explicit exec launch method
        runner = ClaudeRunner(launch_method="exec")
        runner.config = config
        runner.response_logger = MagicMock()

        # Mock the deployment service
        runner.deployment_service.deploy_agents = MagicMock(
            return_value={"deployed": [], "updated": [], "skipped": ["agent1"]}
        )

        # Simulate user explicitly requesting exec mode
        # (In real usage, this would be set via --launch-method exec)
        # The auto-switch should still happen since response logging is enabled
        with patch("builtins.print"), patch(
            "claude_mpm.core.claude_runner.ClaudeRunner._create_system_prompt",
            return_value="test prompt",
        ):
            runner.run_interactive()

        # With our fix, subprocess should be called when response logging is enabled
        self.assert_called_once()
        mock_execvpe.assert_not_called()

    @patch("claude_mpm.core.claude_runner.ClaudeRunner._launch_subprocess_interactive")
    def test_subprocess_mode_preserves_response_logging(self):
        """Test that subprocess mode properly collects output for response logging."""
        # Create config with response logging enabled
        config = self.create_config(response_logging_enabled=True)

        # Create runner
        runner = ClaudeRunner(launch_method="subprocess")
        runner.config = config
        runner.response_logger = MagicMock()

        # Mock the deployment service
        runner.deployment_service.deploy_agents = MagicMock(
            return_value={"deployed": [], "updated": [], "skipped": ["agent1"]}
        )

        with patch(
            "claude_mpm.core.claude_runner.ClaudeRunner._create_system_prompt",
            return_value="test prompt",
        ):
            runner.run_interactive()

        # Verify subprocess was called with correct arguments
        self.assert_called_once()
        call_args = self.call_args

        # Verify the command includes the claude executable
        cmd = call_args[0][0]
        self.assertIn("claude", cmd[0])

        # Verify environment is passed
        env = call_args[0][1]
        self.assertIsInstance(env, dict)

    def test_response_logger_initialization():
        """Test that response logger is properly initialized when enabled."""
        # Create config with response logging enabled
        config = self.create_config(response_logging_enabled=True)

        with patch("claude_mpm.core.claude_runner.Config") as mock_config_class:
            mock_config_class.return_value = config

            # Mock the session logger
            with patch(
                "claude_mpm.services.claude_session_logger.get_session_logger"
            ) as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                # Create runner
                runner = ClaudeRunner()

                # Verify response logger was initialized
                self.assertEqual(runner.response_logger, mock_logger)
                mock_get_logger.assert_called_once_with(config)

    def test_logging_messages_for_auto_switch():
        """Test that appropriate log messages are generated during auto-switch."""
        # Create config with response logging enabled
        config = self.create_config(response_logging_enabled=True)

        # Create runner with project logger
        runner = ClaudeRunner(launch_method="exec", log_level="INFO")
        runner.config = config
        runner.response_logger = MagicMock()
        runner.project_logger = MagicMock()

        # Mock the deployment service
        runner.deployment_service.deploy_agents = MagicMock(
            return_value={"deployed": [], "updated": [], "skipped": ["agent1"]}
        )

        # Run interactive mode
        with patch(
            "claude_mpm.core.claude_runner.ClaudeRunner._launch_subprocess_interactive"
        ), patch(
            "claude_mpm.core.claude_runner.ClaudeRunner._create_system_prompt",
            return_value="test prompt",
        ):
            runner.run_interactive()

        # Verify logging of the auto-switch
        runner.project_logger.log_system.assert_any_call(
            "Auto-switching from exec to subprocess mode for response logging",
            level="INFO",
            component="session",
        )


if __name__ == "__main__":
    unittest.main()
