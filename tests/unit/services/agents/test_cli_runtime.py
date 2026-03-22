"""Tests for CLIAgentRunner — CLI subprocess-based AgentRuntime adapter."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from claude_mpm.services.agents.agent_runtime import (
    AgentConfig,
    AgentResult,
    AgentRuntime,
)
from claude_mpm.services.agents.cli_runtime import CLIAgentRunner

# ---------------------------------------------------------------------------
# Basic interface conformance
# ---------------------------------------------------------------------------


class TestCLIAgentRunnerInterface:
    """Verify CLIAgentRunner implements the AgentRuntime ABC correctly."""

    def test_implements_agent_runtime(self) -> None:
        runner = CLIAgentRunner()
        assert isinstance(runner, AgentRuntime)

    def test_runtime_name_is_cli(self) -> None:
        runner = CLIAgentRunner()
        assert runner.runtime_name == "cli"

    def test_from_config_creates_runner(self) -> None:
        config = AgentConfig(
            system_prompt="Test prompt",
            model="sonnet",
            cwd="/tmp",
            max_turns=5,
        )
        runner = CLIAgentRunner.from_config(config)
        assert isinstance(runner, CLIAgentRunner)
        assert runner._system_prompt == "Test prompt"
        assert runner._model == "sonnet"
        assert runner._cwd == "/tmp"
        assert runner._max_turns == 5

    def test_from_config_with_defaults(self) -> None:
        config = AgentConfig()
        runner = CLIAgentRunner.from_config(config)
        assert runner._system_prompt is None
        assert runner._model is None
        assert runner._cwd is None
        assert runner._max_turns is None


# ---------------------------------------------------------------------------
# run_with_hooks raises NotImplementedError
# ---------------------------------------------------------------------------


class TestRunWithHooksNotSupported:
    """CLI runtime does not support tool interception."""

    @pytest.mark.asyncio
    async def test_run_with_hooks_raises(self) -> None:
        runner = CLIAgentRunner()
        with pytest.raises(NotImplementedError, match="Tool interception"):
            await runner.run_with_hooks("hello")


# ---------------------------------------------------------------------------
# CLI argument building
# ---------------------------------------------------------------------------


class TestBuildCLIArgs:
    """Verify _build_cli_args produces correct argument lists."""

    def test_basic_prompt(self) -> None:
        runner = CLIAgentRunner()
        args = runner._build_cli_args("hello world")
        assert args[0] == "claude"
        assert "-p" in args
        assert "--output-format" in args
        assert "json" in args
        assert args[-1] == "hello world"

    def test_with_model(self) -> None:
        runner = CLIAgentRunner(model="opus")
        args = runner._build_cli_args("hello")
        assert "--model" in args
        idx = args.index("--model")
        assert args[idx + 1] == "opus"

    def test_with_max_turns(self) -> None:
        runner = CLIAgentRunner(max_turns=10)
        args = runner._build_cli_args("hello")
        assert "--max-turns" in args
        idx = args.index("--max-turns")
        assert args[idx + 1] == "10"

    def test_with_resume(self) -> None:
        runner = CLIAgentRunner()
        args = runner._build_cli_args("hello", resume_session="sess-123")
        assert "--resume" in args
        idx = args.index("--resume")
        assert args[idx + 1] == "sess-123"

    def test_with_fork(self) -> None:
        runner = CLIAgentRunner()
        args = runner._build_cli_args("hello", resume_session="sess-123", fork=True)
        assert "--resume" in args
        assert "--fork-session" in args

    def test_with_system_prompt(self) -> None:
        runner = CLIAgentRunner(system_prompt="Be concise")
        args = runner._build_cli_args("hello")
        assert "--system-prompt" in args
        idx = args.index("--system-prompt")
        assert args[idx + 1] == "Be concise"


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------


class TestParseOutput:
    """Verify _parse_output handles various CLI output formats."""

    def test_parse_json_output(self) -> None:
        data = {
            "result": "Hello, world!",
            "session_id": "sess-abc",
            "cost_usd": 0.01,
            "num_turns": 3,
            "is_error": False,
        }
        result = CLIAgentRunner._parse_output(json.dumps(data), duration_ms=100)
        assert result.text == "Hello, world!"
        assert result.session_id == "sess-abc"
        assert result.cost_usd == 0.01
        assert result.num_turns == 3
        assert result.duration_ms == 100
        assert result.is_error is False

    def test_parse_plain_text_fallback(self) -> None:
        result = CLIAgentRunner._parse_output("just plain text\n", duration_ms=50)
        assert result.text == "just plain text"
        assert result.session_id is None
        assert result.duration_ms == 50

    def test_parse_error_output(self) -> None:
        data = {"result": "failed", "is_error": True}
        result = CLIAgentRunner._parse_output(json.dumps(data))
        assert result.is_error is True


# ---------------------------------------------------------------------------
# Subprocess invocation (mocked)
# ---------------------------------------------------------------------------


class TestCLIRun:
    """Test run() with mocked subprocess."""

    @pytest.mark.asyncio
    async def test_run_success(self) -> None:
        runner = CLIAgentRunner()
        output = json.dumps({"result": "Answer", "session_id": "s1"})

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (output.encode(), b"")
        mock_proc.returncode = 0

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            result = await runner.run("test prompt")

        assert isinstance(result, AgentResult)
        assert result.text == "Answer"
        assert result.session_id == "s1"
        assert result.is_error is False
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_failure(self) -> None:
        runner = CLIAgentRunner()

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"Something went wrong")
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await runner.run("test prompt")

        assert result.is_error is True
        assert "Something went wrong" in result.text

    @pytest.mark.asyncio
    async def test_resume_passes_session_id(self) -> None:
        runner = CLIAgentRunner()
        output = json.dumps({"result": "Resumed"})

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (output.encode(), b"")
        mock_proc.returncode = 0

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            result = await runner.resume("sess-xyz", "follow up")

        assert result.text == "Resumed"
        # Verify --resume was in the args
        call_args = mock_exec.call_args[0]
        assert "--resume" in call_args
        assert "sess-xyz" in call_args

    @pytest.mark.asyncio
    async def test_fork_passes_flags(self) -> None:
        runner = CLIAgentRunner()
        output = json.dumps({"result": "Forked"})

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (output.encode(), b"")
        mock_proc.returncode = 0

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            result = await runner.fork("sess-xyz", "branch prompt")

        assert result.text == "Forked"
        call_args = mock_exec.call_args[0]
        assert "--resume" in call_args
        assert "--fork-session" in call_args
