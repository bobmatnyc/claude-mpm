"""Tests for ClaudeMPMSubprocess wrapper.

Tests subprocess creation, command building, and session management.
All subprocess operations are mocked to avoid actual claude-mpm execution.
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.mcp.errors import SessionError
from claude_mpm.mcp.models import SessionResult
from claude_mpm.mcp.subprocess_wrapper import ClaudeMPMSubprocess


class TestClaudeMPMSubprocessInit:
    """Tests for ClaudeMPMSubprocess initialization."""

    def test_default_working_directory(self):
        """Should use current directory as default working directory."""
        wrapper = ClaudeMPMSubprocess()

        assert wrapper.working_directory == str(Path.cwd())

    def test_custom_working_directory(self):
        """Should use provided working directory."""
        wrapper = ClaudeMPMSubprocess(working_directory="/custom/path")

        assert wrapper.working_directory == "/custom/path"

    def test_initial_process_is_none(self):
        """Process should be None before starting."""
        wrapper = ClaudeMPMSubprocess()

        assert wrapper.process is None

    def test_initial_session_id_is_none(self):
        """Session ID should be None before starting."""
        wrapper = ClaudeMPMSubprocess()

        assert wrapper.session_id is None


class TestPrepareEnvironment:
    """Tests for _prepare_environment() method."""

    def test_includes_base_environment(self):
        """Should include base OS environment variables."""
        wrapper = ClaudeMPMSubprocess()

        env = wrapper._prepare_environment()

        # Should have environment variables from os.environ
        assert "PATH" in env or len(env) > 0

    def test_sets_disable_telemetry(self):
        """Should set DISABLE_TELEMETRY=1."""
        wrapper = ClaudeMPMSubprocess()

        env = wrapper._prepare_environment()

        assert env["DISABLE_TELEMETRY"] == "1"

    def test_sets_ci_mode(self):
        """Should set CI=true for non-interactive mode."""
        wrapper = ClaudeMPMSubprocess()

        env = wrapper._prepare_environment()

        assert env["CI"] == "true"

    def test_sets_user_pwd(self):
        """Should set CLAUDE_MPM_USER_PWD to working directory."""
        wrapper = ClaudeMPMSubprocess(working_directory="/test/project")

        env = wrapper._prepare_environment()

        assert env["CLAUDE_MPM_USER_PWD"] == "/test/project"

    def test_applies_overrides(self):
        """Should apply custom environment overrides."""
        wrapper = ClaudeMPMSubprocess()

        env = wrapper._prepare_environment({"CUSTOM_VAR": "value"})

        assert env["CUSTOM_VAR"] == "value"

    def test_overrides_can_replace_defaults(self):
        """Overrides should be able to replace default values."""
        wrapper = ClaudeMPMSubprocess()

        env = wrapper._prepare_environment({"CI": "false"})

        assert env["CI"] == "false"


class TestBuildCommand:
    """Tests for _build_command() method."""

    def test_basic_command(self):
        """Should build basic command with required arguments."""
        wrapper = ClaudeMPMSubprocess()

        cmd = wrapper._build_command(prompt="Hello")

        assert cmd[0] == "claude-mpm"
        assert cmd[1] == "run"
        assert "--headless" in cmd
        assert "--non-interactive" in cmd
        assert "-i" in cmd
        assert "Hello" in cmd

    def test_prompt_is_last_argument(self):
        """Prompt should be passed with -i flag."""
        wrapper = ClaudeMPMSubprocess()

        cmd = wrapper._build_command(prompt="Test prompt")

        i_index = cmd.index("-i")
        assert cmd[i_index + 1] == "Test prompt"

    def test_no_hooks_flag(self):
        """Should include --no-hooks when specified."""
        wrapper = ClaudeMPMSubprocess()

        cmd = wrapper._build_command(prompt="Test", no_hooks=True)

        assert "--no-hooks" in cmd

    def test_no_tickets_flag(self):
        """Should include --no-tickets when specified."""
        wrapper = ClaudeMPMSubprocess()

        cmd = wrapper._build_command(prompt="Test", no_tickets=True)

        assert "--no-tickets" in cmd

    def test_resume_session(self):
        """Should include --resume with session ID."""
        wrapper = ClaudeMPMSubprocess()

        cmd = wrapper._build_command(prompt="Continue", resume_session="sess-123")

        assert "--resume" in cmd
        resume_index = cmd.index("--resume")
        assert cmd[resume_index + 1] == "sess-123"

    def test_fork_with_resume(self):
        """Should include --fork-session when forking."""
        wrapper = ClaudeMPMSubprocess()

        cmd = wrapper._build_command(
            prompt="Fork", resume_session="sess-123", fork=True
        )

        assert "--resume" in cmd
        assert "--fork-session" in cmd

    def test_fork_without_resume_ignored(self):
        """Fork flag should be ignored without resume_session."""
        wrapper = ClaudeMPMSubprocess()

        cmd = wrapper._build_command(prompt="Test", fork=True)

        assert "--fork-session" not in cmd

    def test_all_flags_combined(self):
        """Should handle all flags together."""
        wrapper = ClaudeMPMSubprocess()

        cmd = wrapper._build_command(
            prompt="Full test",
            resume_session="sess-456",
            fork=True,
            no_hooks=True,
            no_tickets=True,
        )

        assert "--no-hooks" in cmd
        assert "--no-tickets" in cmd
        assert "--resume" in cmd
        assert "--fork-session" in cmd
        assert "Full test" in cmd


class TestStartSession:
    """Tests for start_session() method."""

    @pytest.mark.asyncio
    async def test_creates_subprocess(self):
        """start_session should create subprocess with correct args."""
        wrapper = ClaudeMPMSubprocess(working_directory="/test/dir")

        mock_process = MagicMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[
                b'{"session_id": "new-sess-123"}\n',
                b"",
            ]
        )
        mock_process.stderr = MagicMock()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ) as mock_create:
            _session_id, _process = await wrapper.start_session(prompt="Hello")

            # Verify subprocess was created
            mock_create.assert_called_once()
            call_args = mock_create.call_args

            # Check command includes expected elements
            args = call_args[0]
            assert args[0] == "claude-mpm"
            assert "run" in args
            assert "--headless" in args
            assert "Hello" in args

            # Check subprocess options
            kwargs = call_args[1]
            assert kwargs["cwd"] == "/test/dir"
            assert kwargs["stdout"] == asyncio.subprocess.PIPE
            assert kwargs["stderr"] == asyncio.subprocess.PIPE

    @pytest.mark.asyncio
    async def test_extracts_session_id(self):
        """start_session should extract session_id from output."""
        wrapper = ClaudeMPMSubprocess()

        mock_process = MagicMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[
                b'{"session_id": "extracted-id"}\n',
                b"",
            ]
        )

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ):
            session_id, _ = await wrapper.start_session(prompt="Test")

            assert session_id == "extracted-id"
            assert wrapper.session_id == "extracted-id"

    @pytest.mark.asyncio
    async def test_generates_fallback_session_id(self):
        """start_session should generate ID if not in output."""
        wrapper = ClaudeMPMSubprocess()

        mock_process = MagicMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ):
            session_id, _ = await wrapper.start_session(prompt="Test")

            assert session_id.startswith("mpm-")
            assert len(session_id) == 12  # "mpm-" + 8 hex chars

    @pytest.mark.asyncio
    async def test_passes_no_hooks_flag(self):
        """start_session should pass no_hooks to command."""
        wrapper = ClaudeMPMSubprocess()

        mock_process = MagicMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[b'{"session_id": "test"}\n', b""]
        )

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ) as mock_create:
            await wrapper.start_session(prompt="Test", no_hooks=True)

            args = mock_create.call_args[0]
            assert "--no-hooks" in args

    @pytest.mark.asyncio
    async def test_passes_no_tickets_flag(self):
        """start_session should pass no_tickets to command."""
        wrapper = ClaudeMPMSubprocess()

        mock_process = MagicMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[b'{"session_id": "test"}\n', b""]
        )

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ) as mock_create:
            await wrapper.start_session(prompt="Test", no_tickets=True)

            args = mock_create.call_args[0]
            assert "--no-tickets" in args


class TestContinueSession:
    """Tests for continue_session() method."""

    @pytest.mark.asyncio
    async def test_creates_subprocess_with_resume(self):
        """continue_session should create subprocess with --resume."""
        wrapper = ClaudeMPMSubprocess()

        mock_process = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ) as mock_create:
            await wrapper.continue_session(session_id="existing-123", prompt="Continue")

            args = mock_create.call_args[0]
            assert "--resume" in args
            resume_idx = args.index("--resume")
            assert args[resume_idx + 1] == "existing-123"

    @pytest.mark.asyncio
    async def test_sets_session_id(self):
        """continue_session should set session_id."""
        wrapper = ClaudeMPMSubprocess()

        mock_process = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ):
            await wrapper.continue_session(session_id="cont-456", prompt="Next")

            assert wrapper.session_id == "cont-456"

    @pytest.mark.asyncio
    async def test_fork_flag(self):
        """continue_session should pass --fork-session when fork=True."""
        wrapper = ClaudeMPMSubprocess()

        mock_process = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        with patch(
            "asyncio.create_subprocess_exec",
            return_value=mock_process,
        ) as mock_create:
            await wrapper.continue_session(
                session_id="fork-789", prompt="Fork it", fork=True
            )

            args = mock_create.call_args[0]
            assert "--fork-session" in args


class TestWaitForCompletion:
    """Tests for wait_for_completion() method."""

    @pytest.mark.asyncio
    async def test_raises_error_if_not_started(self):
        """wait_for_completion should raise SessionError if process not started."""
        wrapper = ClaudeMPMSubprocess()

        with pytest.raises(SessionError) as exc_info:
            await wrapper.wait_for_completion()

        assert "not started" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_returns_session_result(self):
        """wait_for_completion should return SessionResult."""
        wrapper = ClaudeMPMSubprocess()
        wrapper._session_id = "test-session"

        mock_process = MagicMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[
                b'{"type": "assistant", "message": {"content": "Hello"}}\n',
                b'{"type": "result", "subtype": "success"}\n',
                b"",
            ]
        )
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        wrapper.process = mock_process

        result = await wrapper.wait_for_completion()

        assert isinstance(result, SessionResult)
        assert result.success is True
        assert result.session_id == "test-session"

    @pytest.mark.asyncio
    async def test_captures_messages(self):
        """wait_for_completion should capture all messages."""
        wrapper = ClaudeMPMSubprocess()
        wrapper._session_id = "msg-test"

        mock_process = MagicMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[
                b'{"type": "message", "content": "1"}\n',
                b'{"type": "message", "content": "2"}\n',
                b'{"type": "result", "subtype": "success"}\n',
                b"",
            ]
        )
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        wrapper.process = mock_process

        result = await wrapper.wait_for_completion()

        assert len(result.messages) == 3

    @pytest.mark.asyncio
    async def test_handles_timeout(self):
        """wait_for_completion should handle timeout."""
        wrapper = ClaudeMPMSubprocess()
        wrapper._session_id = "timeout-test"

        mock_process = MagicMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.stderr = AsyncMock()
        mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_process.terminate = MagicMock()
        mock_process.returncode = None  # Simulate running process
        wrapper.process = mock_process

        with pytest.raises(SessionError) as exc_info:
            await wrapper.wait_for_completion(timeout=1.0)

        assert "timed out" in str(exc_info.value).lower()
        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_result_on_failure(self):
        """wait_for_completion should capture error on failure."""
        wrapper = ClaudeMPMSubprocess()
        wrapper._session_id = "error-test"

        mock_process = MagicMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[
                b'{"type": "result", "subtype": "error", "error": "Failed"}\n',
                b"",
            ]
        )
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=1)
        wrapper.process = mock_process

        result = await wrapper.wait_for_completion()

        assert result.success is False
        assert result.error == "Failed"


class TestTerminate:
    """Tests for terminate() method."""

    @pytest.mark.asyncio
    async def test_does_nothing_if_no_process(self):
        """terminate should do nothing if process not started."""
        wrapper = ClaudeMPMSubprocess()

        # Should not raise
        await wrapper.terminate()

    @pytest.mark.asyncio
    async def test_terminates_process(self):
        """terminate should call process.terminate()."""
        wrapper = ClaudeMPMSubprocess()

        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.returncode = None  # Simulate running process
        wrapper.process = mock_process

        await wrapper.terminate()

        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_kills_on_timeout(self):
        """terminate should kill process if terminate times out."""
        wrapper = ClaudeMPMSubprocess()

        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock(side_effect=[asyncio.TimeoutError(), None])
        mock_process.returncode = None  # Simulate running process
        wrapper.process = mock_process

        await wrapper.terminate(force=True)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()


class TestStreamOutput:
    """Tests for stream_output() method."""

    @pytest.mark.asyncio
    async def test_raises_error_if_not_started(self):
        """stream_output should raise SessionError if process not started."""
        wrapper = ClaudeMPMSubprocess()

        with pytest.raises(SessionError):
            async for _ in wrapper.stream_output():
                pass

    @pytest.mark.asyncio
    async def test_yields_parsed_messages(self):
        """stream_output should yield parsed NDJSON messages."""
        wrapper = ClaudeMPMSubprocess()
        wrapper._session_id = "stream-test"

        mock_process = MagicMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[
                b'{"type": "message", "content": "first"}\n',
                b'{"type": "message", "content": "second"}\n',
                b"",
            ]
        )
        wrapper.process = mock_process

        messages = []
        async for msg in wrapper.stream_output():
            messages.append(msg)

        assert len(messages) == 2
        assert messages[0]["content"] == "first"
        assert messages[1]["content"] == "second"


class TestFormatAssistantOutput:
    """Tests for _format_assistant_output() method."""

    def test_handles_string_content(self):
        """_format_assistant_output should handle string content."""
        wrapper = ClaudeMPMSubprocess()
        wrapper.parser.messages = [
            {"type": "assistant", "message": {"content": "Hello world"}},
            {"type": "assistant", "message": {"content": "Second message"}},
        ]

        result = wrapper._format_assistant_output()

        assert "Hello world" in result
        assert "Second message" in result

    def test_handles_content_block_format(self):
        """_format_assistant_output should handle Claude's content block format."""
        wrapper = ClaudeMPMSubprocess()
        wrapper.parser.messages = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "First block"},
                        {"type": "text", "text": "Second block"},
                    ]
                },
            },
        ]

        result = wrapper._format_assistant_output()

        assert "First block" in result
        assert "Second block" in result

    def test_handles_mixed_content_types(self):
        """_format_assistant_output should handle mixed content types."""
        wrapper = ClaudeMPMSubprocess()
        wrapper.parser.messages = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Text content"},
                        {"type": "tool_use", "name": "some_tool"},  # Non-text block
                    ]
                },
            },
        ]

        result = wrapper._format_assistant_output()

        assert "Text content" in result
        assert "some_tool" not in result

    def test_handles_empty_content(self):
        """_format_assistant_output should handle empty content."""
        wrapper = ClaudeMPMSubprocess()
        wrapper.parser.messages = [
            {"type": "assistant", "message": {"content": ""}},
            {"type": "assistant", "message": {"content": []}},
        ]

        result = wrapper._format_assistant_output()

        assert result == ""

    def test_ignores_non_assistant_messages(self):
        """_format_assistant_output should only process assistant messages."""
        wrapper = ClaudeMPMSubprocess()
        wrapper.parser.messages = [
            {"type": "user", "message": {"content": "User message"}},
            {"type": "assistant", "message": {"content": "Assistant message"}},
            {"type": "tool", "message": {"content": "Tool output"}},
        ]

        result = wrapper._format_assistant_output()

        assert "Assistant message" in result
        assert "User message" not in result
        assert "Tool output" not in result
