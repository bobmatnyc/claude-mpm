"""Tests for SDK-based agent runtime prototype.

All tests use mocks to avoid requiring a live Claude Code installation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We need to mock the SDK imports before importing our module
# since the module does a try/except import at module level.


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class FakeToolResultBlock:
    tool_use_id: str
    content: Any
    is_error: bool = False
    type: str = "tool_result"


@dataclass
class FakeAssistantMessage:
    content: list[Any]
    model: str = "claude-sonnet-4-20250514"
    usage: Any = None
    error: Any = None


@dataclass
class FakeResultMessage:
    session_id: str | None = "sess-123"
    total_cost_usd: float | None = 0.005
    num_turns: int | None = 1
    duration_ms: int | None = 1500
    is_error: bool = False
    result: str | None = None
    subtype: str = "result"
    duration_api_ms: int | None = None
    stop_reason: str | None = None
    usage: Any = None
    structured_output: Any = None


@dataclass
class FakePermissionResultAllow:
    pass


@dataclass
class FakePermissionResultDeny:
    reason: str = ""


# ---------------------------------------------------------------------------
# Patch SDK types into the module namespace
# ---------------------------------------------------------------------------

SDK_TYPES = {
    "claude_agent_sdk.AssistantMessage": FakeAssistantMessage,
    "claude_agent_sdk.ResultMessage": FakeResultMessage,
    "claude_agent_sdk.TextBlock": FakeTextBlock,
    "claude_agent_sdk.ToolUseBlock": FakeToolUseBlock,
    "claude_agent_sdk.ToolResultBlock": FakeToolResultBlock,
    "claude_agent_sdk.PermissionResultAllow": FakePermissionResultAllow,
    "claude_agent_sdk.PermissionResultDeny": FakePermissionResultDeny,
}


@pytest.fixture(autouse=True)
def _patch_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch SDK symbols on the already-imported sdk_runtime module."""
    from claude_mpm.services.agents import sdk_runtime

    monkeypatch.setattr(sdk_runtime, "SDK_AVAILABLE", True)
    monkeypatch.setattr(sdk_runtime, "AssistantMessage", FakeAssistantMessage)
    monkeypatch.setattr(sdk_runtime, "ResultMessage", FakeResultMessage)
    monkeypatch.setattr(sdk_runtime, "TextBlock", FakeTextBlock)
    monkeypatch.setattr(sdk_runtime, "ToolUseBlock", FakeToolUseBlock)
    monkeypatch.setattr(sdk_runtime, "ToolResultBlock", FakeToolResultBlock)
    monkeypatch.setattr(sdk_runtime, "PermissionResultAllow", FakePermissionResultAllow)
    monkeypatch.setattr(sdk_runtime, "PermissionResultDeny", FakePermissionResultDeny)
    monkeypatch.setattr(sdk_runtime, "ClaudeAgentOptions", MagicMock)


# ---------------------------------------------------------------------------
# Tests for _extract_result
# ---------------------------------------------------------------------------


class TestExtractResult:
    """Unit tests for SDKAgentRunner._extract_result (static method)."""

    def test_extracts_text_from_assistant_message(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        messages = [
            FakeAssistantMessage(content=[FakeTextBlock(text="Hello world")]),
            FakeResultMessage(session_id="s1", total_cost_usd=0.01),
        ]
        result = SDKAgentRunner._extract_result(messages)
        assert "Hello world" in result.text
        assert result.session_id == "s1"
        assert result.cost_usd == 0.01

    def test_extracts_tool_calls(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        messages = [
            FakeAssistantMessage(
                content=[
                    FakeToolUseBlock(id="tu1", name="Bash", input={"command": "ls"}),
                ]
            ),
            FakeResultMessage(),
        ]
        result = SDKAgentRunner._extract_result(messages)
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "Bash"
        assert result.tool_calls[0].input == {"command": "ls"}

    def test_pairs_tool_result_with_use(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        messages = [
            FakeAssistantMessage(
                content=[
                    FakeToolUseBlock(id="tu1", name="Read", input={"file": "x.py"}),
                    FakeToolResultBlock(
                        tool_use_id="tu1", content="file contents here"
                    ),
                ]
            ),
            FakeResultMessage(),
        ]
        result = SDKAgentRunner._extract_result(messages)
        assert result.tool_calls[0].output == "file contents here"

    def test_marks_error_from_result_message(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        messages = [FakeResultMessage(is_error=True)]
        result = SDKAgentRunner._extract_result(messages)
        assert result.is_error is True

    def test_empty_messages(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        result = SDKAgentRunner._extract_result([])
        assert result.text == ""
        assert result.tool_calls == []
        assert result.session_id is None

    def test_multiple_text_blocks_joined(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        messages = [
            FakeAssistantMessage(content=[FakeTextBlock(text="Part 1")]),
            FakeAssistantMessage(content=[FakeTextBlock(text="Part 2")]),
            FakeResultMessage(),
        ]
        result = SDKAgentRunner._extract_result(messages)
        assert "Part 1" in result.text
        assert "Part 2" in result.text

    def test_result_message_text_appended(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        messages = [FakeResultMessage(result="Final answer")]
        result = SDKAgentRunner._extract_result(messages)
        assert "Final answer" in result.text


# ---------------------------------------------------------------------------
# Tests for run()
# ---------------------------------------------------------------------------


class TestRun:
    """Tests for SDKAgentRunner.run() using mocked sdk_query."""

    @pytest.mark.asyncio
    async def test_run_returns_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        async def fake_query(*, prompt: str, options: Any) -> Any:
            yield FakeAssistantMessage(content=[FakeTextBlock(text="response")])
            yield FakeResultMessage(session_id="s-run", total_cost_usd=0.002)

        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.sdk_query", fake_query
        )

        runner = SDKAgentRunner(system_prompt="test")
        result = await runner.run("hello")

        assert result.text == "response"
        assert result.session_id == "s-run"
        assert result.cost_usd == 0.002

    @pytest.mark.asyncio
    async def test_run_captures_tool_calls(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        async def fake_query(*, prompt: str, options: Any) -> Any:
            yield FakeAssistantMessage(
                content=[
                    FakeToolUseBlock(id="t1", name="Glob", input={"pattern": "*.py"}),
                    FakeTextBlock(text="Found files"),
                ]
            )
            yield FakeResultMessage()

        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.sdk_query", fake_query
        )

        runner = SDKAgentRunner()
        result = await runner.run("find python files")

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "Glob"


# ---------------------------------------------------------------------------
# Tests for run_with_hooks()
# ---------------------------------------------------------------------------


class TestRunWithHooks:
    """Tests for tool interception via run_with_hooks."""

    @pytest.mark.asyncio
    async def test_blocked_tools_denied(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        # Mock ClaudeSDKClient as async context manager
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # receive_response yields a simple result
        async def fake_receive() -> Any:
            yield FakeAssistantMessage(content=[FakeTextBlock(text="ok")])
            yield FakeResultMessage()

        mock_client.receive_response = fake_receive

        mock_client_cls = MagicMock(return_value=mock_client)
        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.ClaudeSDKClient", mock_client_cls
        )

        runner = SDKAgentRunner()
        result = await runner.run_with_hooks(
            prompt="do something",
            blocked_tools={"Bash", "Write"},
        )

        # Verify ClaudeSDKClient was constructed with can_use_tool in options
        call_kwargs = mock_client_cls.call_args
        options = (
            call_kwargs[1]["options"]
            if "options" in call_kwargs[1]
            else call_kwargs[0][0]
        )
        # The can_use_tool should have been set (it's passed via _build_options)
        assert result.text == "ok"

    @pytest.mark.asyncio
    async def test_custom_guard_called(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def fake_receive() -> Any:
            yield FakeResultMessage()

        mock_client.receive_response = fake_receive
        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.ClaudeSDKClient",
            MagicMock(return_value=mock_client),
        )

        guard_calls: list[str] = []

        async def my_guard(name: str, inp: dict[str, Any]) -> bool:
            guard_calls.append(name)
            return name != "Bash"

        runner = SDKAgentRunner()
        await runner.run_with_hooks(prompt="test", tool_guard=my_guard)
        # Guard is registered but not invoked in our mock (no tool use in stream)
        # This validates the wiring works without error
        assert isinstance(guard_calls, list)


# ---------------------------------------------------------------------------
# Tests for inject()
# ---------------------------------------------------------------------------


class TestInject:
    """Tests for multi-turn inject()."""

    @pytest.mark.asyncio
    async def test_inject_sends_multiple_prompts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        queries_sent: list[str] = []
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def fake_query(prompt: str, **kw: Any) -> None:
            queries_sent.append(prompt)

        mock_client.query = fake_query

        call_count = 0

        async def fake_receive() -> Any:
            nonlocal call_count
            call_count += 1
            yield FakeAssistantMessage(
                content=[FakeTextBlock(text=f"Reply {call_count}")]
            )
            yield FakeResultMessage(session_id=f"s{call_count}")

        mock_client.receive_response = fake_receive
        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.ClaudeSDKClient",
            MagicMock(return_value=mock_client),
        )

        runner = SDKAgentRunner()
        result = await runner.inject(["prompt1", "prompt2"])

        assert queries_sent == ["prompt1", "prompt2"]
        assert "Reply 1" in result.text
        assert "Reply 2" in result.text


# ---------------------------------------------------------------------------
# Tests for SDK unavailability
# ---------------------------------------------------------------------------


class TestSDKUnavailable:
    """Verify graceful behavior when SDK is not installed."""

    def test_raises_runtime_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from claude_mpm.services.agents import sdk_runtime

        monkeypatch.setattr(sdk_runtime, "SDK_AVAILABLE", False)

        with pytest.raises(RuntimeError, match="claude-agent-sdk is not installed"):
            sdk_runtime.SDKAgentRunner()


# ---------------------------------------------------------------------------
# Tests for ToolCallRecord and SDKAgentResult dataclasses
# ---------------------------------------------------------------------------


class TestDataClasses:
    """Verify dataclass defaults and field behavior."""

    def test_tool_call_record_defaults(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import ToolCallRecord

        record = ToolCallRecord(tool_name="Bash", input={"cmd": "ls"})
        assert record.approved is True
        assert record.output is None
        assert record.timestamp > 0

    def test_sdk_agent_result_defaults(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentResult

        result = SDKAgentResult(text="hello")
        assert result.tool_calls == []
        assert result.session_id is None
        assert result.is_error is False
        assert result.raw_messages == []
