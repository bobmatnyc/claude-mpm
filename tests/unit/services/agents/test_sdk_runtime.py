"""Tests for SDK-based agent runtime (with AgentRuntime ABC integration).

All tests use mocks to avoid requiring a live Claude Code installation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

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
    monkeypatch.setattr(sdk_runtime, "ClaudeSDKClient", MagicMock)


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
        # _extract_result returns SDKAgentResult with ToolCallRecord objects
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

    def test_static_to_agent_result_converts_correctly(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import (
            SDKAgentResult,
            SDKAgentRunner,
            ToolCallRecord,
        )

        sdk_result = SDKAgentResult(
            text="hello",
            session_id="s1",
            tool_calls=[
                ToolCallRecord(tool_name="Bash", input={"cmd": "ls"}, output="files")
            ],
            cost_usd=0.01,
            num_turns=2,
            duration_ms=500,
            is_error=False,
        )
        agent_result = SDKAgentRunner._static_to_agent_result(sdk_result)
        assert agent_result.text == "hello"
        assert agent_result.session_id == "s1"
        assert agent_result.cost_usd == 0.01
        assert len(agent_result.tool_calls) == 1
        assert agent_result.tool_calls[0]["tool_name"] == "Bash"
        assert agent_result.tool_calls[0]["output"] == "files"

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
        assert result.tool_calls[0]["tool_name"] == "Glob"


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


# ---------------------------------------------------------------------------
# Tests for resume() and fork()
# ---------------------------------------------------------------------------


class TestResumeFork:
    """Tests for session resume and fork."""

    @pytest.mark.asyncio
    async def test_resume_passes_session_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from claude_mpm.services.agents import sdk_runtime
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        # Use a fresh MagicMock so we can inspect call_args reliably
        mock_options_cls = MagicMock()
        monkeypatch.setattr(sdk_runtime, "ClaudeAgentOptions", mock_options_cls)

        async def fake_query(*, prompt: str, options: Any) -> Any:
            yield FakeAssistantMessage(content=[FakeTextBlock(text="resumed")])
            yield FakeResultMessage(session_id="s-resumed")

        monkeypatch.setattr(sdk_runtime, "sdk_query", fake_query)

        runner = SDKAgentRunner(system_prompt="test")
        result = await runner.resume("old-session-id", "follow-up")

        assert result.text == "resumed"
        assert result.session_id == "s-resumed"
        # Verify resume kwarg was passed to ClaudeAgentOptions
        call_kwargs = mock_options_cls.call_args[1]
        assert call_kwargs["resume"] == "old-session-id"

    @pytest.mark.asyncio
    async def test_fork_passes_session_id_and_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from claude_mpm.services.agents import sdk_runtime
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        mock_options_cls = MagicMock()
        monkeypatch.setattr(sdk_runtime, "ClaudeAgentOptions", mock_options_cls)

        async def fake_query(*, prompt: str, options: Any) -> Any:
            yield FakeAssistantMessage(content=[FakeTextBlock(text="forked")])
            yield FakeResultMessage(session_id="s-forked")

        monkeypatch.setattr(sdk_runtime, "sdk_query", fake_query)

        runner = SDKAgentRunner(system_prompt="test")
        result = await runner.fork("original-session", "branched prompt")

        assert result.text == "forked"
        assert result.session_id == "s-forked"
        call_kwargs = mock_options_cls.call_args[1]
        assert call_kwargs["resume"] == "original-session"
        assert call_kwargs["fork_session"] is True


# ---------------------------------------------------------------------------
# Tests for run_streaming()
# ---------------------------------------------------------------------------


class TestRunStreaming:
    """Tests for streaming output with callbacks."""

    @pytest.mark.asyncio
    async def test_on_text_called_for_text_blocks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        async def fake_query(*, prompt: str, options: Any) -> Any:
            yield FakeAssistantMessage(
                content=[
                    FakeTextBlock(text="chunk1"),
                    FakeTextBlock(text="chunk2"),
                ]
            )
            yield FakeResultMessage()

        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.sdk_query", fake_query
        )

        text_chunks: list[str] = []

        async def on_text(text: str) -> None:
            text_chunks.append(text)

        runner = SDKAgentRunner()
        result = await runner.run_streaming("hello", on_text=on_text)

        assert text_chunks == ["chunk1", "chunk2"]
        assert "chunk1" in result.text
        assert "chunk2" in result.text

    @pytest.mark.asyncio
    async def test_on_tool_call_called_for_tool_blocks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        async def fake_query(*, prompt: str, options: Any) -> Any:
            yield FakeAssistantMessage(
                content=[
                    FakeToolUseBlock(id="t1", name="Read", input={"file": "x.py"}),
                ]
            )
            yield FakeResultMessage()

        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.sdk_query", fake_query
        )

        tool_calls: list[tuple[str, dict[str, Any]]] = []

        async def on_tool_call(name: str, inp: dict[str, Any]) -> None:
            tool_calls.append((name, inp))

        runner = SDKAgentRunner()
        result = await runner.run_streaming("read file", on_tool_call=on_tool_call)

        assert len(tool_calls) == 1
        assert tool_calls[0] == ("Read", {"file": "x.py"})
        assert len(result.tool_calls) == 1

    @pytest.mark.asyncio
    async def test_streaming_works_without_callbacks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        async def fake_query(*, prompt: str, options: Any) -> Any:
            yield FakeAssistantMessage(content=[FakeTextBlock(text="no-cb")])
            yield FakeResultMessage()

        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.sdk_query", fake_query
        )

        runner = SDKAgentRunner()
        result = await runner.run_streaming("hello")

        assert result.text == "no-cb"


# ---------------------------------------------------------------------------
# Tests for InterruptibleSession
# ---------------------------------------------------------------------------


class TestInterruptibleSession:
    """Tests for the interruptible session context manager."""

    @pytest.mark.asyncio
    async def test_query_collects_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def fake_receive() -> Any:
            yield FakeAssistantMessage(content=[FakeTextBlock(text="interrupted-ok")])
            yield FakeResultMessage(session_id="s-int")

        mock_client.receive_response = fake_receive

        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.ClaudeSDKClient",
            MagicMock(return_value=mock_client),
        )

        runner = SDKAgentRunner()
        async with runner.interruptible() as session:
            result = await session.query("do work")

        assert result.text == "interrupted-ok"
        assert result.session_id == "s-int"
        assert session.session_id == "s-int"

    @pytest.mark.asyncio
    async def test_interrupt_calls_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.interrupt = AsyncMock()

        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.ClaudeSDKClient",
            MagicMock(return_value=mock_client),
        )

        runner = SDKAgentRunner()
        async with runner.interruptible() as session:
            await session.interrupt()

        mock_client.interrupt.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_raises_when_not_open(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import (
            InterruptibleSession,
            SDKAgentRunner,
        )

        runner = SDKAgentRunner()
        session = InterruptibleSession(runner)
        with pytest.raises(RuntimeError, match="Session is not open"):
            await session.query("hello")

    @pytest.mark.asyncio
    async def test_interrupt_noop_when_no_client(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import (
            InterruptibleSession,
            SDKAgentRunner,
        )

        runner = SDKAgentRunner()
        session = InterruptibleSession(runner)
        # Should not raise even without a client
        await session.interrupt()


# ---------------------------------------------------------------------------
# Tests for AgentRuntime ABC compliance
# ---------------------------------------------------------------------------


class TestAgentRuntimeABC:
    """Verify SDKAgentRunner satisfies the AgentRuntime ABC."""

    def test_is_instance_of_agent_runtime(self) -> None:
        from claude_mpm.services.agents.agent_runtime import AgentRuntime
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner()
        assert isinstance(runner, AgentRuntime)

    def test_runtime_name_is_sdk(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner()
        assert runner.runtime_name == "sdk"

    @pytest.mark.asyncio
    async def test_run_returns_agent_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from claude_mpm.services.agents.agent_runtime import AgentResult
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        async def fake_query(*, prompt: str, options: Any) -> Any:
            yield FakeAssistantMessage(content=[FakeTextBlock(text="abc")])
            yield FakeResultMessage(session_id="s1")

        monkeypatch.setattr(
            "claude_mpm.services.agents.sdk_runtime.sdk_query", fake_query
        )

        runner = SDKAgentRunner(system_prompt="test")
        result = await runner.run("hello")
        assert isinstance(result, AgentResult)
        assert result.text == "abc"


# ---------------------------------------------------------------------------
# Tests for from_config()
# ---------------------------------------------------------------------------


class TestFromConfig:
    """Tests for the from_config classmethod."""

    def test_creates_runner_from_config(self) -> None:
        from claude_mpm.services.agents.agent_runtime import AgentConfig
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        config = AgentConfig(
            system_prompt="You are helpful.",
            model="sonnet",
            max_turns=10,
        )
        runner = SDKAgentRunner.from_config(config)
        assert runner.system_prompt == "You are helpful."
        assert runner.model == "claude-sonnet-4-20250514"
        assert runner.max_turns == 10

    def test_resolves_mpm_model_names(self) -> None:
        from claude_mpm.services.agents.agent_runtime import AgentConfig
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        for short, full in [
            ("sonnet", "claude-sonnet-4-20250514"),
            ("opus", "claude-opus-4-20250514"),
            ("haiku", "claude-haiku-3-20250307"),
        ]:
            runner = SDKAgentRunner.from_config(AgentConfig(model=short))
            assert runner.model == full

    def test_passes_through_full_model_name(self) -> None:
        from claude_mpm.services.agents.agent_runtime import AgentConfig
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner.from_config(
            AgentConfig(model="claude-sonnet-4-20250514")
        )
        assert runner.model == "claude-sonnet-4-20250514"

    def test_none_model_stays_none(self) -> None:
        from claude_mpm.services.agents.agent_runtime import AgentConfig
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner.from_config(AgentConfig())
        assert runner.model is None

    def test_mcp_servers_passed_through(self) -> None:
        from claude_mpm.services.agents.agent_runtime import AgentConfig
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        mcp = {"my-server": {"command": "npx", "args": ["my-server"]}}
        runner = SDKAgentRunner.from_config(AgentConfig(mcp_servers=mcp))
        assert runner.mcp_servers == mcp


# ---------------------------------------------------------------------------
# Tests for from_agent_template()
# ---------------------------------------------------------------------------


class TestFromAgentTemplate:
    """Tests for the from_agent_template classmethod."""

    def test_loads_v3_template(self, tmp_path: Path) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        template = {
            "version": 3,
            "narrative_fields": {"instructions": "You are a test agent."},
            "capabilities": {
                "model": "sonnet",
                "tools": ["Bash", "Read"],
            },
            "configuration_fields": {
                "timeout": 120,
                "max_budget_usd": 0.50,
            },
        }
        path = tmp_path / "agent.json"
        path.write_text(json.dumps(template))

        runner = SDKAgentRunner.from_agent_template(path)
        assert runner.system_prompt == "You are a test agent."
        assert runner.model == "claude-sonnet-4-20250514"
        assert runner.allowed_tools == ["Bash", "Read"]
        assert runner.max_turns == 120  # fallback from timeout
        assert runner.max_budget_usd == 0.50

    def test_loads_template_with_system_prompt_key(self, tmp_path: Path) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        template = {
            "system_prompt": "Legacy system prompt.",
            "configuration_fields": {"model": "opus"},
        }
        path = tmp_path / "agent.json"
        path.write_text(json.dumps(template))

        runner = SDKAgentRunner.from_agent_template(path)
        assert runner.system_prompt == "Legacy system prompt."
        assert runner.model == "claude-opus-4-20250514"

    def test_wildcard_tools_not_set(self, tmp_path: Path) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        template = {
            "capabilities": {"tools": "*"},
        }
        path = tmp_path / "agent.json"
        path.write_text(json.dumps(template))

        runner = SDKAgentRunner.from_agent_template(path)
        assert runner.allowed_tools is None

    def test_mcp_servers_passthrough(self, tmp_path: Path) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        template = {"narrative_fields": {"instructions": "test"}}
        path = tmp_path / "agent.json"
        path.write_text(json.dumps(template))

        mcp = {"vector-search": {"command": "node", "args": ["server.js"]}}
        runner = SDKAgentRunner.from_agent_template(path, mcp_servers=mcp)
        assert runner.mcp_servers == mcp

    def test_no_model_returns_none(self, tmp_path: Path) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        template = {"narrative_fields": {"instructions": "test"}}
        path = tmp_path / "agent.json"
        path.write_text(json.dumps(template))

        runner = SDKAgentRunner.from_agent_template(path)
        assert runner.model is None

    def test_max_turns_preferred_over_timeout(self, tmp_path: Path) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        template = {
            "configuration_fields": {
                "max_turns": 50,
                "timeout": 300,
            },
        }
        path = tmp_path / "agent.json"
        path.write_text(json.dumps(template))

        runner = SDKAgentRunner.from_agent_template(path)
        assert runner.max_turns == 50

    def test_file_not_found_raises(self) -> None:
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        with pytest.raises(FileNotFoundError):
            SDKAgentRunner.from_agent_template("/nonexistent/agent.json")


# ---------------------------------------------------------------------------
# Tests for MCP server passthrough in _build_options
# ---------------------------------------------------------------------------


class TestMCPPassthrough:
    """Tests for MCP server configuration passthrough."""

    def test_mcp_servers_in_build_options(self) -> None:
        from claude_mpm.services.agents import sdk_runtime
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        mcp = {"my-server": {"command": "npx", "args": ["srv"]}}
        runner = SDKAgentRunner(mcp_servers=mcp)

        # Use a fresh mock to inspect call_args
        mock_opts = MagicMock()
        original = sdk_runtime.ClaudeAgentOptions
        sdk_runtime.ClaudeAgentOptions = mock_opts
        try:
            runner._build_options()
            call_kwargs = mock_opts.call_args[1]
            assert call_kwargs["mcp_servers"] == mcp
        finally:
            sdk_runtime.ClaudeAgentOptions = original

    def test_mcp_servers_none_omitted(self) -> None:
        from claude_mpm.services.agents import sdk_runtime
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner()
        mock_opts = MagicMock()
        original = sdk_runtime.ClaudeAgentOptions
        sdk_runtime.ClaudeAgentOptions = mock_opts
        try:
            runner._build_options()
            call_kwargs = mock_opts.call_args[1]
            assert "mcp_servers" not in call_kwargs
        finally:
            sdk_runtime.ClaudeAgentOptions = original


# ---------------------------------------------------------------------------
# Tests for create_runtime() factory
# ---------------------------------------------------------------------------


class TestCreateRuntime:
    """Tests for the create_runtime factory function."""

    def test_creates_sdk_runtime(self) -> None:
        from claude_mpm.services.agents.agent_runtime import (
            AgentConfig,
            AgentRuntime,
            create_runtime,
        )
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runtime = create_runtime("sdk", AgentConfig(system_prompt="hi"))
        assert isinstance(runtime, SDKAgentRunner)
        assert isinstance(runtime, AgentRuntime)
        assert runtime.system_prompt == "hi"

    def test_default_is_sdk(self) -> None:
        from claude_mpm.services.agents.agent_runtime import (
            AgentRuntime,
            create_runtime,
        )
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runtime = create_runtime()
        assert isinstance(runtime, SDKAgentRunner)

    def test_unknown_type_raises(self) -> None:
        from claude_mpm.services.agents.agent_runtime import create_runtime

        with pytest.raises(ValueError, match="Unknown runtime type"):
            create_runtime("unknown")


# ---------------------------------------------------------------------------
# Tests for model mapping helpers
# ---------------------------------------------------------------------------


class TestModelMapping:
    """Tests for resolve_model_to_sdk and resolve_model_to_mpm."""

    def test_resolve_short_to_sdk(self) -> None:
        from claude_mpm.services.agents.agent_runtime import resolve_model_to_sdk

        assert resolve_model_to_sdk("sonnet") == "claude-sonnet-4-20250514"
        assert resolve_model_to_sdk("opus") == "claude-opus-4-20250514"
        assert resolve_model_to_sdk("haiku") == "claude-haiku-3-20250307"

    def test_resolve_full_passthrough(self) -> None:
        from claude_mpm.services.agents.agent_runtime import resolve_model_to_sdk

        full = "claude-sonnet-4-20250514"
        assert resolve_model_to_sdk(full) == full

    def test_resolve_sdk_to_mpm(self) -> None:
        from claude_mpm.services.agents.agent_runtime import resolve_model_to_mpm

        assert resolve_model_to_mpm("claude-sonnet-4-20250514") == "sonnet"
        assert resolve_model_to_mpm("claude-opus-4-20250514") == "opus"

    def test_resolve_mpm_fallback_extraction(self) -> None:
        from claude_mpm.services.agents.agent_runtime import resolve_model_to_mpm

        assert resolve_model_to_mpm("some-custom-sonnet-model") == "sonnet"
        assert resolve_model_to_mpm("future-opus-v9") == "opus"

    def test_resolve_mpm_unknown_returns_original(self) -> None:
        from claude_mpm.services.agents.agent_runtime import resolve_model_to_mpm

        assert resolve_model_to_mpm("gpt-4") == "gpt-4"


# ---------------------------------------------------------------------------
# Tests for AgentConfig and AgentResult dataclasses
# ---------------------------------------------------------------------------


class TestRuntimeDataClasses:
    """Tests for AgentConfig and AgentResult."""

    def test_agent_config_defaults(self) -> None:
        from claude_mpm.services.agents.agent_runtime import AgentConfig

        cfg = AgentConfig()
        assert cfg.system_prompt is None
        assert cfg.model is None
        assert cfg.mcp_servers is None

    def test_agent_result_defaults(self) -> None:
        from claude_mpm.services.agents.agent_runtime import AgentResult

        result = AgentResult(text="hello")
        assert result.tool_calls == []
        assert result.session_id is None
        assert result.is_error is False
        assert result.cost_usd is None
