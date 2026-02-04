"""
Comprehensive tests for headless mode feature.

WHY: Headless mode is essential for CI/CD pipelines, Vibe Kanban integration,
and programmatic automation. These tests ensure it works correctly.

Test coverage:
1. CLI flag parsing tests
2. Command building tests
3. Argument filtering tests
4. Integration tests (with mocked os.execvpe)
5. End-to-end workflow tests

Note: These tests verify command building and argument handling.
The actual os.execvpe() execution is mocked since it replaces the process.
"""

import io
import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.cli.commands.run import filter_claude_mpm_args, _run_headless_session
from claude_mpm.cli.parsers.run_parser import add_run_arguments
from claude_mpm.core.headless_session import HeadlessSession


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_runner():
    """Create a mock runner object for HeadlessSession."""
    runner = Mock()
    runner.claude_args = []
    return runner


@pytest.fixture
def headless_session(mock_runner):
    """Create a HeadlessSession instance for testing."""
    with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
        return HeadlessSession(mock_runner)


@pytest.fixture
def base_args():
    """Create base CLI arguments for testing."""
    return Namespace(
        headless=False,
        input=None,
        non_interactive=False,
        no_hooks=False,
        no_tickets=False,
        claude_args=[],
        logging="INFO",
        resume=None,
        mpm_resume=None,
        # Claude Code passthrough flags
        passthrough_print=False,
        dangerously_skip_permissions=False,
        output_format=None,
        input_format=None,
        include_partial_messages=False,
        disallowedTools=None,
    )


@pytest.fixture
def headless_args(base_args):
    """Create headless CLI arguments for testing."""
    base_args.headless = True
    return base_args


# =============================================================================
# 1. CLI Flag Parsing Tests
# =============================================================================


class TestCLIFlagParsing:
    """Test CLI flag parsing for headless mode."""

    def test_headless_flag_recognized(self):
        """--headless flag should be parsed without error."""
        import argparse
        parser = argparse.ArgumentParser()
        add_run_arguments(parser)

        args = parser.parse_args(["--headless"])
        assert args.headless is True

    def test_headless_flag_default_false(self):
        """--headless flag should default to False."""
        import argparse
        parser = argparse.ArgumentParser()
        add_run_arguments(parser)

        args = parser.parse_args([])
        assert args.headless is False

    def test_resume_flag_recognized(self):
        """--resume <session_id> should be parsed correctly."""
        import argparse
        parser = argparse.ArgumentParser()
        add_run_arguments(parser)

        args = parser.parse_args(["--resume", "abc123"])
        assert args.resume == "abc123"

    def test_resume_flag_without_argument(self):
        """--resume without argument should use empty string (resume last)."""
        import argparse
        parser = argparse.ArgumentParser()
        add_run_arguments(parser)

        args = parser.parse_args(["--resume"])
        assert args.resume == ""  # Empty string means resume last session

    def test_resume_flag_default_none(self):
        """--resume flag should default to None when not used."""
        import argparse
        parser = argparse.ArgumentParser()
        add_run_arguments(parser)

        args = parser.parse_args([])
        assert args.resume is None

    def test_headless_with_resume_combined(self):
        """--headless --resume can be combined."""
        import argparse
        parser = argparse.ArgumentParser()
        add_run_arguments(parser)

        args = parser.parse_args(["--headless", "--resume", "session123"])
        assert args.headless is True
        assert args.resume == "session123"

    def test_headless_with_input_flag(self):
        """--headless with -i flag should work."""
        import argparse
        parser = argparse.ArgumentParser()
        add_run_arguments(parser)

        args = parser.parse_args(["--headless", "-i", "test prompt"])
        assert args.headless is True
        assert args.input == "test prompt"

    def test_mpm_resume_flag_recognized(self):
        """--mpm-resume flag should be parsed correctly."""
        import argparse
        parser = argparse.ArgumentParser()
        add_run_arguments(parser)

        args = parser.parse_args(["--mpm-resume", "session456"])
        assert args.mpm_resume == "session456"

    def test_mpm_resume_without_argument(self):
        """--mpm-resume without argument should use 'last'."""
        import argparse
        parser = argparse.ArgumentParser()
        add_run_arguments(parser)

        args = parser.parse_args(["--mpm-resume"])
        assert args.mpm_resume == "last"


# =============================================================================
# 2. Command Building Tests
# =============================================================================


class TestCommandBuilding:
    """Test HeadlessSession command building."""

    def test_base_command_includes_stream_json(self, headless_session):
        """Headless command should include --output-format stream-json."""
        cmd = headless_session.build_claude_command()

        assert "claude" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        # Verify order
        idx = cmd.index("--output-format")
        assert cmd[idx + 1] == "stream-json"

    def test_command_with_resume_session(self, mock_runner):
        """Resume command should include --resume with session ID."""
        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        cmd = session.build_claude_command(resume_session="abc123")

        assert "--resume" in cmd
        assert "abc123" in cmd
        idx = cmd.index("--resume")
        assert cmd[idx + 1] == "abc123"

    def test_command_with_custom_claude_args(self, mock_runner):
        """Custom claude_args should be included in command."""
        mock_runner.claude_args = ["--model", "opus", "--verbose"]

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        cmd = session.build_claude_command()

        assert "--model" in cmd
        assert "opus" in cmd

    def test_command_skips_duplicate_resume(self, mock_runner):
        """Command should not duplicate --resume flag."""
        mock_runner.claude_args = ["--resume", "old_session"]

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        cmd = session.build_claude_command(resume_session="new_session")

        # Should only have one --resume with new_session
        resume_indices = [i for i, arg in enumerate(cmd) if arg == "--resume"]
        assert len(resume_indices) == 1
        assert cmd[resume_indices[0] + 1] == "new_session"

    def test_command_preserves_output_format_passthrough(self, mock_runner):
        """Should not add stream-json if output-format already specified."""
        mock_runner.claude_args = ["--output-format", "json"]

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        cmd = session.build_claude_command()

        # Should preserve the passthrough format
        output_format_indices = [i for i, arg in enumerate(cmd) if arg == "--output-format"]
        assert len(output_format_indices) == 1

    def test_command_includes_verbose(self, mock_runner):
        """Headless command should include --verbose for stream-json."""
        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        cmd = session.build_claude_command()

        assert "--verbose" in cmd


# =============================================================================
# 3. Argument Filtering Tests
# =============================================================================


class TestArgumentFiltering:
    """Test filtering of MPM-specific arguments."""

    def test_filter_removes_headless_flag(self):
        """filter_claude_mpm_args should remove --headless."""
        args = ["--headless", "--model", "opus"]
        filtered = filter_claude_mpm_args(args)

        assert "--headless" not in filtered
        assert "--model" in filtered
        assert "opus" in filtered

    def test_filter_removes_monitor_flags(self):
        """filter_claude_mpm_args should remove --monitor and --websocket-port."""
        args = ["--monitor", "--websocket-port", "8765", "--verbose"]
        filtered = filter_claude_mpm_args(args)

        assert "--monitor" not in filtered
        assert "--websocket-port" not in filtered
        assert "8765" not in filtered
        assert "--verbose" in filtered

    def test_filter_removes_mpm_specific_flags(self):
        """filter_claude_mpm_args should remove all MPM-specific flags."""
        args = [
            "--no-hooks", "--no-tickets", "--launch-method", "vscode",
            "--model", "sonnet"
        ]
        filtered = filter_claude_mpm_args(args)

        assert "--no-hooks" not in filtered
        assert "--no-tickets" not in filtered
        assert "--launch-method" not in filtered
        assert "vscode" not in filtered
        assert "--model" in filtered
        assert "sonnet" in filtered

    def test_filter_handles_empty_list(self):
        """filter_claude_mpm_args should handle empty list."""
        assert filter_claude_mpm_args([]) == []

    def test_filter_handles_none(self):
        """filter_claude_mpm_args should handle None."""
        assert filter_claude_mpm_args(None) == []

    def test_multiple_mpm_flags(self):
        """Multiple MPM flags should all be filtered."""
        args = [
            "--monitor", "--websocket-port", "8765",
            "--no-hooks", "--no-tickets", "--headless",
            "--model", "sonnet"
        ]
        filtered = filter_claude_mpm_args(args)

        assert len(filtered) == 2  # Only --model and sonnet
        assert "--model" in filtered
        assert "sonnet" in filtered


# =============================================================================
# 4. Integration Tests (with mocked os.execvpe)
# =============================================================================


class TestHeadlessIntegration:
    """Integration tests for headless mode with mocked os.execvpe.

    Note: os.execvpe() replaces the current process and never returns
    on success. We mock it to verify the command that would be executed.
    """

    def test_run_calls_execvpe_with_correct_command(self, mock_runner):
        """Headless run should call os.execvpe with properly built command."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("os.chdir"):
            with patch("claude_mpm.core.headless_session.os.execvpe") as mock_exec:
                # execvpe never returns, so we simulate that by raising SystemExit
                mock_exec.side_effect = SystemExit(0)

                try:
                    session.run(prompt="test prompt")
                except SystemExit:
                    pass

                # Verify execvpe was called
                mock_exec.assert_called_once()

                # Get the command that would be executed
                call_args = mock_exec.call_args
                cmd = call_args[0][1]  # Second positional arg is command list
                env = call_args[0][2]  # Third positional arg is environment

                # Verify command structure
                assert cmd[0] == "claude"
                assert "--output-format" in cmd
                assert "stream-json" in cmd
                assert "--print" in cmd
                assert "test prompt" in cmd

    def test_run_includes_resume_in_command(self, mock_runner):
        """Headless run with resume should include --resume in command."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("os.chdir"):
            with patch("claude_mpm.core.headless_session.os.execvpe") as mock_exec:
                mock_exec.side_effect = SystemExit(0)

                try:
                    session.run(prompt="test prompt", resume_session="abc123")
                except SystemExit:
                    pass

                cmd = mock_exec.call_args[0][1]
                assert "--resume" in cmd
                assert "abc123" in cmd

    def test_run_changes_to_working_directory(self, mock_runner):
        """Headless run should chdir to working directory before exec."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test/project")):
            session = HeadlessSession(mock_runner)

        with patch("os.chdir") as mock_chdir:
            with patch("claude_mpm.core.headless_session.os.execvpe") as mock_exec:
                mock_exec.side_effect = SystemExit(0)

                try:
                    session.run(prompt="test prompt")
                except SystemExit:
                    pass

                mock_chdir.assert_called_with("/test/project")

    def test_run_handles_file_not_found(self, mock_runner):
        """Headless run should handle Claude CLI not found."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("os.chdir"):
            with patch("claude_mpm.core.headless_session.os.execvpe") as mock_exec:
                mock_exec.side_effect = FileNotFoundError("claude not found")

                with patch("sys.stderr.write") as mock_stderr:
                    with patch("sys.stderr.flush"):
                        exit_code = session.run(prompt="test prompt")

                assert exit_code == 127  # Standard "command not found" exit code
                mock_stderr.assert_called()

    def test_run_handles_permission_error(self, mock_runner):
        """Headless run should handle permission denied."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("os.chdir"):
            with patch("claude_mpm.core.headless_session.os.execvpe") as mock_exec:
                mock_exec.side_effect = PermissionError("Permission denied")

                with patch("sys.stderr.write"):
                    with patch("sys.stderr.flush"):
                        exit_code = session.run(prompt="test prompt")

                assert exit_code == 126  # Standard "permission denied" exit code

    def test_environment_sets_disable_telemetry(self, mock_runner):
        """Headless run should set DISABLE_TELEMETRY=1."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        env = session._prepare_environment()

        assert env.get("DISABLE_TELEMETRY") == "1"

    def test_environment_sets_ci_true(self, mock_runner):
        """Headless run should set CI=true."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        env = session._prepare_environment()

        assert env.get("CI") == "true"

    def test_run_passes_through_custom_claude_args(self, mock_runner):
        """Custom claude_args should be passed to os.execvpe."""
        mock_runner.claude_args = ["--model", "opus"]

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("os.chdir"):
            with patch("claude_mpm.core.headless_session.os.execvpe") as mock_exec:
                mock_exec.side_effect = SystemExit(0)

                try:
                    session.run(prompt="test prompt")
                except SystemExit:
                    pass

                cmd = mock_exec.call_args[0][1]
                assert "--model" in cmd
                assert "opus" in cmd


# =============================================================================
# 5. Empty Prompt and Stdin Tests
# =============================================================================


class TestPromptHandling:
    """Test prompt handling in headless mode."""

    def test_empty_prompt_returns_error(self, mock_runner):
        """Empty prompt should return error exit code."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("sys.stderr.write"):
            with patch("sys.stderr.flush"):
                exit_code = session.run(prompt="")

        assert exit_code == 1

    def test_none_prompt_with_tty_returns_error(self, mock_runner):
        """None prompt with TTY stdin should return error (no piped input)."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stderr.write"):
                with patch("sys.stderr.flush"):
                    exit_code = session.run(prompt=None)

        assert exit_code == 1

    def test_reads_prompt_from_stdin(self, mock_runner):
        """Should read prompt from stdin when not TTY."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.read", return_value="piped prompt\n"):
                with patch("os.chdir"):
                    with patch("claude_mpm.core.headless_session.os.execvpe") as mock_exec:
                        mock_exec.side_effect = SystemExit(0)

                        try:
                            session.run(prompt=None)
                        except SystemExit:
                            pass

                        cmd = mock_exec.call_args[0][1]
                        assert "piped prompt" in cmd


# =============================================================================
# 6. _run_headless_session Function Tests
# =============================================================================


class TestRunHeadlessSessionFunction:
    """Test the _run_headless_session function from run.py."""

    def test_run_headless_session_basic(self, headless_args):
        """_run_headless_session should work with basic args."""
        headless_args.input = "test prompt"

        with patch("os.chdir"):
            with patch("claude_mpm.core.headless_session.os.execvpe") as mock_exec:
                mock_exec.side_effect = SystemExit(0)

                try:
                    _run_headless_session(headless_args)
                except SystemExit:
                    pass

                mock_exec.assert_called_once()
                cmd = mock_exec.call_args[0][1]
                assert "claude" in cmd
                assert "test prompt" in cmd

    def test_run_headless_session_with_resume(self, headless_args):
        """_run_headless_session should handle --resume flag."""
        headless_args.input = "test prompt"
        headless_args.resume = "session123"

        with patch("os.chdir"):
            with patch("claude_mpm.core.headless_session.os.execvpe") as mock_exec:
                mock_exec.side_effect = SystemExit(0)

                try:
                    _run_headless_session(headless_args)
                except SystemExit:
                    pass

                cmd = mock_exec.call_args[0][1]
                assert "--resume" in cmd
                assert "session123" in cmd
                assert "--fork-session" in cmd

    def test_run_headless_session_passthrough_flags(self, headless_args):
        """_run_headless_session should pass through Claude flags."""
        headless_args.input = "test prompt"
        headless_args.dangerously_skip_permissions = True
        headless_args.output_format = "json"

        with patch("os.chdir"):
            with patch("claude_mpm.core.headless_session.os.execvpe") as mock_exec:
                mock_exec.side_effect = SystemExit(0)

                try:
                    _run_headless_session(headless_args)
                except SystemExit:
                    pass

                cmd = mock_exec.call_args[0][1]
                assert "--dangerously-skip-permissions" in cmd
                assert "--output-format" in cmd
                assert "json" in cmd


# =============================================================================
# 7. Stream-JSON Input Tests
# =============================================================================


class TestStreamJsonInput:
    """Test stream-json input mode (Vibe Kanban compatibility)."""

    def test_detects_stream_json_input_format(self, mock_runner):
        """Should detect --input-format stream-json."""
        mock_runner.claude_args = ["--input-format", "stream-json"]

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        # The session should detect stream-json input mode
        claude_args = session.runner.claude_args or []
        uses_stream_json = (
            "--input-format=stream-json" in claude_args
            or session._has_adjacent_args(claude_args, "--input-format", "stream-json")
        )
        assert uses_stream_json is True

    def test_detects_stream_json_input_format_equals(self, mock_runner):
        """Should detect --input-format=stream-json (equals format)."""
        mock_runner.claude_args = ["--input-format=stream-json"]

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        claude_args = session.runner.claude_args or []
        uses_stream_json = "--input-format=stream-json" in claude_args
        assert uses_stream_json is True


# =============================================================================
# 8. Resume Mode Detection Tests
# =============================================================================


class TestResumeModeDetection:
    """Test resume mode detection for system prompt handling."""

    def test_is_resume_mode_with_session_arg(self, mock_runner):
        """_is_resume_mode should return True when resume_session is provided."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        # Test with resume_session argument
        assert session._is_resume_mode(resume_session="abc123") is True

    def test_is_resume_mode_with_claude_args(self, mock_runner):
        """_is_resume_mode should return True when --resume in claude_args."""
        mock_runner.claude_args = ["--resume", "session123"]

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        assert session._is_resume_mode() is True

    def test_is_resume_mode_false_for_new_session(self, mock_runner):
        """_is_resume_mode should return False for new sessions."""
        mock_runner.claude_args = ["--model", "opus"]

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        assert session._is_resume_mode() is False


# =============================================================================
# 9. Hook Verification Tests
# =============================================================================


class TestHookVerification:
    """Test hook verification in headless mode."""

    def test_verify_hooks_warns_on_issues(self, mock_runner):
        """Should warn to stderr when hook issues are detected."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        mock_installer = Mock()
        mock_installer.verify_hooks.return_value = (False, ["Hook not installed"])

        # Patch at the import location within the method
        with patch.dict("sys.modules", {"claude_mpm.hooks.claude_hooks.installer": Mock(HookInstaller=Mock(return_value=mock_installer))}):
            with patch("sys.stderr.write") as mock_stderr:
                with patch("sys.stderr.flush"):
                    session._verify_hooks_deployed()

        mock_stderr.assert_called()
        # Verify warning was written to stderr
        call_args = str(mock_stderr.call_args_list)
        assert "Warning" in call_args or "Hook" in call_args

    def test_verify_hooks_silent_on_success(self, mock_runner):
        """Should not write to stderr when hooks are valid."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        mock_installer = Mock()
        mock_installer.verify_hooks.return_value = (True, [])

        with patch.dict("sys.modules", {"claude_mpm.hooks.claude_hooks.installer": Mock(HookInstaller=Mock(return_value=mock_installer))}):
            with patch("sys.stderr.write") as mock_stderr:
                session._verify_hooks_deployed()

        mock_stderr.assert_not_called()

    def test_verify_hooks_handles_exception(self, mock_runner):
        """Should handle exceptions gracefully without crashing."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        # Make the import succeed but the verification fail with exception
        mock_installer = Mock()
        mock_installer.verify_hooks.side_effect = Exception("Unexpected error")

        with patch.dict("sys.modules", {"claude_mpm.hooks.claude_hooks.installer": Mock(HookInstaller=Mock(return_value=mock_installer))}):
            # Should not raise - exceptions are caught and logged
            session._verify_hooks_deployed()
