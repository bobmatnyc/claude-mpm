"""
Comprehensive tests for headless mode feature.

WHY: Headless mode is essential for CI/CD pipelines, Vibe Kanban integration,
and programmatic automation. These tests ensure it works correctly.

Test coverage:
1. CLI flag parsing tests
2. Command building tests
3. Argument filtering tests
4. Integration tests (with mocked subprocess)
5. End-to-end workflow tests
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
from claude_mpm.core.headless_session import HeadlessSession, run_headless


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

    def test_command_preserves_custom_claude_args(self, mock_runner):
        """Custom claude_args should be preserved in command."""
        mock_runner.claude_args = ["--model", "sonnet", "--verbose"]
        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        cmd = session.build_claude_command()

        assert "--model" in cmd
        assert "sonnet" in cmd
        assert "--verbose" in cmd

    def test_command_deduplicates_resume_flag(self, mock_runner):
        """When resume_session is provided, skip --resume from runner.claude_args."""
        mock_runner.claude_args = ["--resume", "old_session", "--model", "sonnet"]
        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        cmd = session.build_claude_command(resume_session="new_session")

        # Should have new_session, not old_session
        assert "new_session" in cmd
        assert "old_session" not in cmd
        # --resume should appear only once
        assert cmd.count("--resume") == 1

    def test_command_filters_fork_session_when_resume_provided(self, mock_runner):
        """--fork-session from runner.claude_args should be skipped when resume_session provided."""
        mock_runner.claude_args = ["--fork-session", "--model", "sonnet"]
        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        cmd = session.build_claude_command(resume_session="abc123")

        assert "--fork-session" not in cmd
        assert "--model" in cmd

    def test_command_without_resume(self, headless_session):
        """Command without resume should not include --resume flag."""
        cmd = headless_session.build_claude_command()

        assert "--resume" not in cmd


# =============================================================================
# 3. Argument Filtering Tests
# =============================================================================


class TestArgumentFiltering:
    """Test filter_claude_mpm_args function."""

    def test_filters_monitor_flag(self):
        """--monitor should be filtered out."""
        args = ["--monitor", "--model", "sonnet"]
        filtered = filter_claude_mpm_args(args)

        assert "--monitor" not in filtered
        assert "--model" in filtered
        assert "sonnet" in filtered

    def test_filters_headless_flag(self):
        """--headless should be filtered out."""
        args = ["--headless", "--model", "sonnet"]
        filtered = filter_claude_mpm_args(args)

        assert "--headless" not in filtered
        assert "--model" in filtered

    def test_filters_websocket_port_with_value(self):
        """--websocket-port and its value should be filtered out."""
        args = ["--websocket-port", "9000", "--model", "sonnet"]
        filtered = filter_claude_mpm_args(args)

        assert "--websocket-port" not in filtered
        assert "9000" not in filtered
        assert "--model" in filtered

    def test_filters_input_flag_with_value(self):
        """--input and its value should be filtered out."""
        args = ["--input", "test prompt", "--model", "sonnet"]
        filtered = filter_claude_mpm_args(args)

        assert "--input" not in filtered
        assert "test prompt" not in filtered

    def test_filters_short_input_flag(self):
        """-i and its value should be filtered out."""
        args = ["-i", "test prompt", "--model", "sonnet"]
        filtered = filter_claude_mpm_args(args)

        assert "-i" not in filtered
        assert "test prompt" not in filtered

    def test_filters_no_hooks_flag(self):
        """--no-hooks should be filtered out."""
        args = ["--no-hooks", "--model", "sonnet"]
        filtered = filter_claude_mpm_args(args)

        assert "--no-hooks" not in filtered

    def test_filters_no_tickets_flag(self):
        """--no-tickets should be filtered out."""
        args = ["--no-tickets", "--model", "sonnet"]
        filtered = filter_claude_mpm_args(args)

        assert "--no-tickets" not in filtered

    def test_filters_mpm_resume_with_value(self):
        """--mpm-resume and its value should be filtered out."""
        args = ["--mpm-resume", "abc123", "--model", "sonnet"]
        filtered = filter_claude_mpm_args(args)

        assert "--mpm-resume" not in filtered
        assert "abc123" not in filtered

    def test_filters_mpm_resume_without_value(self):
        """--mpm-resume without value should be filtered (value is optional)."""
        args = ["--mpm-resume", "--model", "sonnet"]
        filtered = filter_claude_mpm_args(args)

        assert "--mpm-resume" not in filtered
        # --model should be preserved (not treated as mpm-resume value since it starts with --)
        assert "--model" in filtered

    def test_removes_double_dash_separator(self):
        """The -- separator should be removed."""
        args = ["--", "--model", "sonnet"]
        filtered = filter_claude_mpm_args(args)

        assert "--" not in filtered
        assert "--model" in filtered

    def test_preserves_genuine_claude_args(self):
        """Genuine Claude CLI arguments should be preserved."""
        args = ["--model", "sonnet", "--verbose", "--system-prompt", "You are helpful"]
        filtered = filter_claude_mpm_args(args)

        assert "--model" in filtered
        assert "sonnet" in filtered
        assert "--verbose" in filtered
        assert "--system-prompt" in filtered
        assert "You are helpful" in filtered

    def test_empty_args(self):
        """Empty args should return empty list."""
        assert filter_claude_mpm_args([]) == []
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
# 4. Integration Tests
# =============================================================================


class TestHeadlessIntegration:
    """Integration tests for headless mode with mocked subprocess."""

    def test_run_outputs_to_stdout(self, mock_runner):
        """Headless run should output to stdout without Rich formatting."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        mock_process = Mock()
        mock_process.communicate.return_value = ('{"type": "result", "data": "test"}\n', "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            with patch("sys.stdout.write") as mock_write:
                with patch("sys.stdout.flush"):
                    exit_code = session.run(prompt="test prompt")

        assert exit_code == 0
        mock_write.assert_called()
        # Verify NDJSON was written to stdout
        write_calls = [call[0][0] for call in mock_write.call_args_list]
        assert any('{"type": "result"' in str(call) for call in write_calls)

    def test_run_preserves_stderr(self, mock_runner):
        """Headless run should pass stderr through."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "Warning: test warning\n")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("sys.stderr.write") as mock_stderr:
                with patch("sys.stderr.flush"):
                    session.run(prompt="test prompt")

        mock_stderr.assert_called()
        write_calls = [call[0][0] for call in mock_stderr.call_args_list]
        assert any("Warning" in str(call) for call in write_calls)

    def test_run_returns_correct_exit_code(self, mock_runner):
        """Headless run should return Claude's exit code."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 42

        with patch("subprocess.Popen", return_value=mock_process):
            exit_code = session.run(prompt="test prompt")

        assert exit_code == 42

    def test_run_handles_file_not_found(self, mock_runner):
        """Headless run should handle Claude CLI not found."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("subprocess.Popen", side_effect=FileNotFoundError("claude not found")):
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

        with patch("subprocess.Popen", side_effect=PermissionError("Permission denied")):
            with patch("sys.stderr.write") as mock_stderr:
                with patch("sys.stderr.flush"):
                    exit_code = session.run(prompt="test prompt")

        assert exit_code == 126  # Standard "permission denied" exit code

    def test_run_uses_print_flag_for_prompt(self, mock_runner):
        """Headless run should use --print flag for prompt."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            session.run(prompt="my test prompt")

        # Get the command passed to Popen
        cmd = mock_popen.call_args[0][0]
        assert "--print" in cmd
        assert "my test prompt" in cmd

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

        exit_code = session.run(prompt="")

        assert exit_code == 1

    def test_none_prompt_with_tty_returns_error(self, mock_runner):
        """None prompt with TTY stdin should return error (no piped input)."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("sys.stdin.isatty", return_value=True):
            exit_code = session.run(prompt=None)

        assert exit_code == 1

    def test_reads_prompt_from_stdin(self, mock_runner):
        """Should read prompt from stdin when not TTY."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin.read", return_value="piped prompt\n"):
                with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
                    exit_code = session.run(prompt=None)

        assert exit_code == 0
        cmd = mock_popen.call_args[0][0]
        assert "piped prompt" in cmd


# =============================================================================
# 6. Run Headless Helper Function Tests
# =============================================================================


class TestRunHeadlessFunction:
    """Test the run_headless convenience function."""

    def test_run_headless_basic(self):
        """run_headless should work with basic arguments."""
        mock_process = Mock()
        mock_process.communicate.return_value = ('{"type": "result"}\n', "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("sys.stdout.write"):
                with patch("sys.stdout.flush"):
                    exit_code = run_headless(prompt="test prompt")

        assert exit_code == 0

    def test_run_headless_with_resume(self):
        """run_headless should handle resume_session."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            run_headless(prompt="test", resume_session="abc123")

        cmd = mock_popen.call_args[0][0]
        assert "--resume" in cmd
        assert "abc123" in cmd

    def test_run_headless_with_custom_args(self):
        """run_headless should pass through custom claude_args."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            run_headless(prompt="test", claude_args=["--model", "opus"])

        cmd = mock_popen.call_args[0][0]
        assert "--model" in cmd
        assert "opus" in cmd


# =============================================================================
# 7. _run_headless_session Function Tests
# =============================================================================


class TestRunHeadlessSessionFunction:
    """Test the _run_headless_session function from run.py."""

    def test_run_headless_session_basic(self, headless_args):
        """_run_headless_session should work with basic args."""
        headless_args.input = "test prompt"

        mock_process = Mock()
        mock_process.communicate.return_value = ('{"type": "result"}\n', "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("sys.stdout.write"):
                with patch("sys.stdout.flush"):
                    exit_code = _run_headless_session(headless_args)

        assert exit_code == 0

    def test_run_headless_session_with_resume(self, headless_args):
        """_run_headless_session should handle --resume flag."""
        headless_args.input = "test prompt"
        headless_args.resume = "session123"

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            _run_headless_session(headless_args)

        cmd = mock_popen.call_args[0][0]
        assert "--resume" in cmd
        assert "session123" in cmd
        assert "--fork-session" in cmd

    def test_run_headless_session_resume_last(self, headless_args):
        """_run_headless_session should handle --resume without session ID."""
        headless_args.input = "test prompt"
        headless_args.resume = ""  # Empty string = resume last

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            _run_headless_session(headless_args)

        cmd = mock_popen.call_args[0][0]
        assert "--resume" in cmd
        # Should NOT have --fork-session when resuming last session
        assert "--fork-session" not in cmd

    def test_run_headless_session_filters_mpm_args(self, headless_args):
        """_run_headless_session should filter MPM-specific args."""
        headless_args.input = "test prompt"
        headless_args.claude_args = ["--", "--monitor", "--model", "sonnet"]

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            _run_headless_session(headless_args)

        cmd = mock_popen.call_args[0][0]
        assert "--monitor" not in cmd
        assert "--model" in cmd


# =============================================================================
# 8. Working Directory Tests
# =============================================================================


class TestWorkingDirectory:
    """Test working directory handling in headless mode."""

    def test_uses_cwd_by_default(self, mock_runner):
        """Should use current working directory by default."""
        with patch("os.environ", {}):
            with patch("pathlib.Path.cwd", return_value=Path("/default/cwd")):
                session = HeadlessSession(mock_runner)

        assert session.working_dir == Path("/default/cwd")

    def test_uses_env_var_when_set(self, mock_runner):
        """Should use CLAUDE_MPM_USER_PWD environment variable when set."""
        with patch.dict("os.environ", {"CLAUDE_MPM_USER_PWD": "/custom/path"}):
            session = HeadlessSession(mock_runner)

        assert session.working_dir == Path("/custom/path")

    def test_subprocess_uses_working_dir(self, mock_runner):
        """Subprocess should be started in the correct working directory."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test/dir")):
            session = HeadlessSession(mock_runner)

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            session.run(prompt="test")

        # Verify cwd was passed to Popen
        popen_kwargs = mock_popen.call_args[1]
        assert popen_kwargs.get("cwd") == "/test/dir"


# =============================================================================
# 9. NDJSON Output Format Tests
# =============================================================================


class TestNDJSONOutput:
    """Test that output is valid NDJSON format."""

    def test_output_passes_through_ndjson(self, mock_runner):
        """Output should be valid NDJSON (one JSON object per line)."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        # Simulate NDJSON output from Claude
        ndjson_output = (
            '{"type": "init", "session_id": "abc123"}\n'
            '{"type": "message", "content": "Hello"}\n'
            '{"type": "result", "status": "success"}\n'
        )

        mock_process = Mock()
        mock_process.communicate.return_value = (ndjson_output, "")
        mock_process.returncode = 0

        captured_output = []

        def capture_write(content):
            captured_output.append(content)

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("sys.stdout.write", side_effect=capture_write):
                with patch("sys.stdout.flush"):
                    session.run(prompt="test")

        # Verify output was passed through
        full_output = "".join(captured_output)

        # Each line should be valid JSON
        for line in full_output.strip().split("\n"):
            if line:
                parsed = json.loads(line)
                assert "type" in parsed


# =============================================================================
# 10. End-to-End Workflow Tests
# =============================================================================


class TestEndToEndWorkflow:
    """Test complete headless workflow scenarios."""

    def test_headless_follow_up_workflow(self, headless_args):
        """Test workflow: initial prompt -> capture session_id -> follow-up."""
        # Simulate initial session response with session_id
        initial_output = '{"type": "init", "session_id": "session-xyz-123"}\n{"type": "result", "status": "success"}\n'

        mock_process = Mock()
        mock_process.communicate.return_value = (initial_output, "")
        mock_process.returncode = 0

        captured_stdout = []

        def capture_stdout(content):
            captured_stdout.append(content)

        headless_args.input = "Start a new task"

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("sys.stdout.write", side_effect=capture_stdout):
                with patch("sys.stdout.flush"):
                    exit_code = _run_headless_session(headless_args)

        assert exit_code == 0

        # Parse output to find session_id
        full_output = "".join(captured_stdout)
        session_id = None
        for line in full_output.strip().split("\n"):
            if line:
                data = json.loads(line)
                if data.get("type") == "init":
                    session_id = data.get("session_id")
                    break

        assert session_id == "session-xyz-123"

        # Now simulate follow-up with resume
        headless_args.input = "Continue the task"
        headless_args.resume = session_id

        captured_stdout.clear()

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            with patch("sys.stdout.write", side_effect=capture_stdout):
                with patch("sys.stdout.flush"):
                    exit_code = _run_headless_session(headless_args)

        # Verify --resume was used with the captured session_id
        cmd = mock_popen.call_args[0][0]
        assert "--resume" in cmd
        assert "session-xyz-123" in cmd
        assert "--fork-session" in cmd

    def test_ci_pipeline_workflow(self, headless_args):
        """Test typical CI/CD pipeline usage."""
        headless_args.input = "Run linting and fix any issues"

        mock_process = Mock()
        mock_process.communicate.return_value = (
            '{"type": "result", "status": "success", "output": "Fixed 3 issues"}\n',
            ""
        )
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            with patch("sys.stdout.write"):
                with patch("sys.stdout.flush"):
                    exit_code = _run_headless_session(headless_args)

        assert exit_code == 0

        # Verify proper command was built
        cmd = mock_popen.call_args[0][0]
        assert "claude" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--print" in cmd
        assert "Run linting and fix any issues" in cmd

    def test_vibe_kanban_integration_workflow(self, headless_args):
        """Test Vibe Kanban integration workflow."""
        # Vibe Kanban passes task description via -i
        headless_args.input = """## Task: Implement user authentication

        ### Requirements:
        - Add login endpoint
        - Add logout endpoint
        - Use JWT tokens
        """

        mock_process = Mock()
        mock_process.communicate.return_value = (
            '{"type": "init", "session_id": "vk-session-001"}\n'
            '{"type": "tool_use", "tool": "Edit", "file": "auth.py"}\n'
            '{"type": "result", "status": "success"}\n',
            ""
        )
        mock_process.returncode = 0

        captured = []

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("sys.stdout.write", side_effect=lambda x: captured.append(x)):
                with patch("sys.stdout.flush"):
                    exit_code = _run_headless_session(headless_args)

        assert exit_code == 0

        # Verify output can be parsed for session info
        output = "".join(captured)
        lines = [json.loads(line) for line in output.strip().split("\n") if line]

        # Should have init with session_id
        init_msg = next((m for m in lines if m.get("type") == "init"), None)
        assert init_msg is not None
        assert "session_id" in init_msg


# =============================================================================
# 11. Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_handles_unexpected_exception(self, mock_runner):
        """Should handle unexpected exceptions gracefully."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        with patch("subprocess.Popen", side_effect=RuntimeError("Unexpected error")):
            with patch("sys.stderr.write") as mock_stderr:
                with patch("sys.stderr.flush"):
                    exit_code = session.run(prompt="test")

        assert exit_code == 1
        mock_stderr.assert_called()

    def test_handles_whitespace_only_prompt(self, mock_runner):
        """Whitespace-only prompt should be passed through (not stripped).

        Note: The implementation does NOT strip prompts provided directly.
        Only prompts read from stdin are stripped. This is by design -
        if you provide a prompt directly, you get what you asked for.
        """
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            exit_code = session.run(prompt="   \n\t  ")

        # The prompt is passed through unchanged
        assert exit_code == 0
        cmd = mock_popen.call_args[0][0]
        assert "--print" in cmd
        assert "   \n\t  " in cmd

    def test_handles_very_long_prompt(self, mock_runner):
        """Should handle very long prompts."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        long_prompt = "A" * 100000  # 100KB prompt

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            exit_code = session.run(prompt=long_prompt)

        assert exit_code == 0
        cmd = mock_popen.call_args[0][0]
        assert long_prompt in cmd

    def test_handles_special_characters_in_prompt(self, mock_runner):
        """Should handle special characters in prompts."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        special_prompt = 'Test with "quotes" and \'apostrophes\' and $variables and `backticks`'

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            exit_code = session.run(prompt=special_prompt)

        assert exit_code == 0
        cmd = mock_popen.call_args[0][0]
        assert special_prompt in cmd

    def test_handles_unicode_prompt(self, mock_runner):
        """Should handle unicode characters in prompts."""
        mock_runner.claude_args = []

        with patch.object(HeadlessSession, "_get_working_directory", return_value=Path("/test")):
            session = HeadlessSession(mock_runner)

        unicode_prompt = "Test with emoji and unicode"

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            exit_code = session.run(prompt=unicode_prompt)

        assert exit_code == 0
