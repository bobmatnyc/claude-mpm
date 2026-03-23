"""Tests for the runtime bridge module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.agents.agent_runtime import AgentConfig, AgentResult
from claude_mpm.services.agents.runtime_bridge import (
    execute_agent_prompt,
    print_runtime_status,
)

# The bridge imports get_runtime/get_runtime_type inside the function body,
# so we must patch them at their *definition* site (runtime_config module).
_PATCH_GET_RUNTIME = "claude_mpm.services.agents.runtime_config.get_runtime"
_PATCH_GET_RUNTIME_TYPE = "claude_mpm.services.agents.runtime_config.get_runtime_type"


@pytest.fixture
def mock_runtime() -> MagicMock:
    """Create a mock AgentRuntime with preset return values."""
    runtime = MagicMock()
    runtime.run = AsyncMock(
        return_value=AgentResult(
            text="4",
            session_id="sess_123",
            cost_usd=0.001,
            num_turns=1,
            duration_ms=500,
            is_error=False,
            tool_calls=[],
        )
    )
    runtime.resume = AsyncMock(
        return_value=AgentResult(
            text="resumed answer",
            session_id="sess_123",
            cost_usd=0.002,
            num_turns=2,
            duration_ms=800,
            is_error=False,
            tool_calls=[],
        )
    )
    return runtime


@pytest.mark.asyncio
async def test_execute_agent_prompt_run_path(mock_runtime: MagicMock) -> None:
    """Test that execute_agent_prompt calls runtime.run when no session_id."""
    with (
        patch(_PATCH_GET_RUNTIME, return_value=mock_runtime),
        patch(_PATCH_GET_RUNTIME_TYPE, return_value="cli"),
    ):
        result = await execute_agent_prompt(
            prompt="What is 2+2?",
            system_prompt="Be concise.",
            model="sonnet",
        )

    assert result["text"] == "4"
    assert result["runtime"] == "cli"
    assert result["session_id"] == "sess_123"
    assert result["is_error"] is False

    mock_runtime.run.assert_called_once()
    call_args = mock_runtime.run.call_args
    assert call_args[0][0] == "What is 2+2?"
    config_arg = call_args[0][1]
    assert isinstance(config_arg, AgentConfig)
    assert config_arg.system_prompt == "Be concise."
    assert config_arg.model == "sonnet"


@pytest.mark.asyncio
async def test_execute_agent_prompt_resume_path(mock_runtime: MagicMock) -> None:
    """Test that execute_agent_prompt calls runtime.resume when session_id provided."""
    with (
        patch(_PATCH_GET_RUNTIME, return_value=mock_runtime),
        patch(_PATCH_GET_RUNTIME_TYPE, return_value="sdk"),
    ):
        result = await execute_agent_prompt(
            prompt="Follow up question",
            session_id="sess_abc",
        )

    assert result["text"] == "resumed answer"
    assert result["runtime"] == "sdk"

    mock_runtime.resume.assert_called_once()
    call_args = mock_runtime.resume.call_args
    assert call_args[0][0] == "sess_abc"
    assert call_args[0][1] == "Follow up question"
    mock_runtime.run.assert_not_called()


@pytest.mark.asyncio
async def test_execute_agent_prompt_result_dict_keys(mock_runtime: MagicMock) -> None:
    """Test that result dict contains all expected keys including runtime."""
    with (
        patch(_PATCH_GET_RUNTIME, return_value=mock_runtime),
        patch(_PATCH_GET_RUNTIME_TYPE, return_value="cli"),
    ):
        result = await execute_agent_prompt(prompt="test")

    expected_keys = {
        "text",
        "session_id",
        "cost_usd",
        "num_turns",
        "duration_ms",
        "is_error",
        "tool_calls",
        "runtime",
    }
    assert set(result.keys()) == expected_keys


@pytest.mark.asyncio
async def test_execute_agent_prompt_passes_config_fields(
    mock_runtime: MagicMock,
) -> None:
    """Test that all config fields are properly passed through."""
    with (
        patch(_PATCH_GET_RUNTIME, return_value=mock_runtime),
        patch(_PATCH_GET_RUNTIME_TYPE, return_value="cli"),
    ):
        await execute_agent_prompt(
            prompt="test",
            cwd="/tmp",
            max_turns=5,
            allowed_tools=["Read", "Bash"],
            mcp_servers={"test": {"command": "echo"}},
        )

    call_args = mock_runtime.run.call_args
    config_arg = call_args[0][1]
    assert config_arg.cwd == "/tmp"
    assert config_arg.max_turns == 5
    assert config_arg.allowed_tools == ["Read", "Bash"]
    assert config_arg.mcp_servers == {"test": {"command": "echo"}}


def test_print_runtime_status_cli(capsys: pytest.CaptureFixture[str]) -> None:
    """Test print_runtime_status outputs runtime info."""
    with (
        patch(_PATCH_GET_RUNTIME_TYPE, return_value="cli"),
        patch.dict("os.environ", {}, clear=False),
    ):
        print_runtime_status()

    captured = capsys.readouterr()
    assert "Runtime: cli" in captured.out
    assert "SDK available:" in captured.out
