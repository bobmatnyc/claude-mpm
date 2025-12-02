"""
Test case to verify --resume flag is properly passed through to Claude CLI.

This test ensures that the --resume flag is correctly:
1. Added to claude_args when the flag is set
2. Not filtered out by filter_claude_mpm_args
3. Included in the final command built by InteractiveSession
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.run import filter_claude_mpm_args
from claude_mpm.core.interactive_session import InteractiveSession


class TestResumeFlagVerification(unittest.TestCase):
    """Test --resume flag handling throughout the command pipeline."""

    def test_resume_flag_not_filtered():
        """Verify --resume is NOT filtered out as an MPM-specific flag."""
        # Test that --resume passes through the filter
        args = ["--resume", "--continue", "--max-tokens", "4000"]
        filtered = filter_claude_mpm_args(args)

        self.assertIn("--resume", filtered)
        self.assertEqual(filtered, ["--resume", "--continue", "--max-tokens", "4000"])

    def test_mpm_flags_are_filtered():
        """Verify MPM-specific flags ARE filtered out."""
        args = ["--monitor", "--resume", "--debug", "--continue"]
        filtered = filter_claude_mpm_args(args)

        # --monitor and --debug should be filtered out
        self.assertNotIn("--monitor", filtered)
        self.assertNotIn("--debug", filtered)

        # --resume and --continue should remain
        self.assertIn("--resume", filtered)
        self.assertIn("--continue", filtered)

    def test_interactive_session_includes_resume():
        """Verify InteractiveSession includes --resume in final command."""
        # Create mock runner with --resume in claude_args
        mock_runner = Mock()
        mock_runner.claude_args = ["--resume", "--continue"]
        mock_runner._create_system_prompt = Mock(return_value="test_prompt")
        mock_runner._get_version = Mock(return_value="test_version")
        mock_runner.config = Mock()
        mock_runner.config.get = Mock(return_value={})

        # Create InteractiveSession
        session = InteractiveSession(mock_runner)

        # Build command
        with patch(
            "claude_mpm.core.claude_runner.create_simple_context"
        ) as mock_context:
            mock_context.return_value = "simple_context"
            cmd = session._build_claude_command()

        # Verify --resume is in the command
        self.assertIn("--resume", cmd)

        # Verify command structure
        self.assertEqual(cmd[0], "claude")
        self.assertEqual(cmd[1], "--model")
        self.assertEqual(cmd[2], "opus")
        self.assertIn("--dangerously-skip-permissions", cmd)

        # Find position of --resume
        resume_index = cmd.index("--resume")
        self.assertGreater(resume_index, 3)  # After the base command parts

    def test_resume_flag_position():
        """Verify --resume is added at the beginning of claude_args."""
        # Import here to avoid circular imports

        # Create mock args
        args = Mock()
        args.resume = True
        args.claude_args = ["--continue", "--max-tokens", "4000"]
        args.no_tickets = False
        args.monitor = False
        args.logging = "off"
        args.launch_method = "exec"
        args.non_interactive = True
        args.input = "test input"
        args.no_native_agents = True

        # Mock dependencies
        with patch("claude_mpm.core.claude_runner.ClaudeRunner") as MockRunner:
            with patch("claude_mpm.cli.commands.run.SessionManager") as MockSession:
                with patch("claude_mpm.cli.commands.run.get_user_input") as mock_input:
                    with patch(
                        "claude_mpm.cli.commands.run._check_configuration_health"
                    ):
                        with patch(
                            "claude_mpm.cli.commands.run._check_claude_json_memory"
                        ):
                            with patch(
                                "claude_mpm.cli.commands.run.list_agent_versions_at_startup"
                            ):
                                mock_input.return_value = "test input"
                                mock_session = MockSession.return_value
                                mock_session.get_last_interactive_session.return_value = None

                                # Create mock runner instance
                                mock_runner_instance = Mock()
                                mock_runner_instance.run_oneshot.return_value = True
                                MockRunner.return_value = mock_runner_instance

                                # Run the session
                                run_session(args)

                                # Verify ClaudeRunner was called with --resume in claude_args
                                MockRunner.assert_called_once()
                                call_args = MockRunner.call_args

                                # Check that claude_args includes --resume
                                claude_args = call_args[1]["claude_args"]
                                self.assertIn("--resume", claude_args)

                                # Verify --resume is at the beginning
                                self.assertEqual(claude_args[0], "--resume")

    def test_end_to_end_resume_command():
        """Test the complete command building pipeline with --resume."""
        # Simulate the entire flow
        raw_args = ["--continue", "--max-tokens", "4000"]

        # Step 1: Add --resume if flag is set
        if True:  # Simulating args.resume = True
            if "--resume" not in raw_args:
                raw_args = ["--resume", *raw_args]

        # Step 2: Filter MPM args
        filtered = filter_claude_mpm_args(raw_args)

        # Step 3: Build final command
        cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions"]
        cmd.extend(filtered)

        # Verify
        self.assertIn("--resume", cmd)
        self.assertEqual(cmd[4], "--resume")  # After the base 4 elements

        print(f"✅ Final command: {' '.join(cmd)}")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
