"""Mock-based equivalents of the SDK integration tests.

These tests validate the same integration contracts as
test_sdk_integration.py (agent invocation, response handling, error paths)
but stub out the SDK runtime and API layer so no real API key or
claude-agent-sdk installation is required.  They run unconditionally in CI.

Covered contracts:
  1. SDKAgentRunner.run() returns AgentResult with expected text and no error.
  2. SDKAgentRunner.run() returns a non-empty session_id string.
  3. SDKAgentRunner.run_streaming() fires on_text callbacks that
     SDKEventBridge captures, and SDKEventBridge.summary() is correct.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixture: inject a fake claude_agent_sdk module so sdk_runtime can import
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fake_sdk_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a minimal fake claude_agent_sdk into sys.modules.

    This lets sdk_runtime.py complete its top-level import block without
    requiring the real package.  Each test then patches sdk_query directly.
    """
    sdk = ModuleType("claude_agent_sdk")

    # Minimal stand-in types that isinstance checks in sdk_runtime need
    class _AssistantMessage:
        pass

    class _ResultMessage:
        pass

    class _TextBlock:
        pass

    class _ToolUseBlock:
        pass

    class _ToolResultBlock:
        pass

    class _ClaudeAgentOptions:
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    class _ClaudeSDKClient:
        pass

    class _PermissionResultAllow:
        pass

    class _PermissionResultDeny:
        def __init__(self, reason: str = "") -> None:
            self.reason = reason

    sdk.AssistantMessage = _AssistantMessage  # type: ignore[attr-defined]
    sdk.ResultMessage = _ResultMessage  # type: ignore[attr-defined]
    sdk.TextBlock = _TextBlock  # type: ignore[attr-defined]
    sdk.ToolUseBlock = _ToolUseBlock  # type: ignore[attr-defined]
    sdk.ToolResultBlock = _ToolResultBlock  # type: ignore[attr-defined]
    sdk.ClaudeAgentOptions = _ClaudeAgentOptions  # type: ignore[attr-defined]
    sdk.ClaudeSDKClient = _ClaudeSDKClient  # type: ignore[attr-defined]
    sdk.PermissionResultAllow = _PermissionResultAllow  # type: ignore[attr-defined]
    sdk.PermissionResultDeny = _PermissionResultDeny  # type: ignore[attr-defined]
    sdk.query = AsyncMock()  # patched per-test below  # type: ignore[attr-defined]

    # Replace or insert the module
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", sdk)

    # Also remove any previously cached sdk_runtime so it re-imports cleanly
    for mod_name in list(sys.modules):
        if "sdk_runtime" in mod_name or "sdk_event_bridge" in mod_name:
            monkeypatch.delitem(sys.modules, mod_name, raising=False)


# ---------------------------------------------------------------------------
# Helpers to build messages whose isinstance checks pass
#
# We retrieve the fake SDK types from sys.modules at call time so that pyright
# does not attempt (and fail) to resolve the uninstalled claude_agent_sdk
# package statically.  All three helpers are only called after the
# fake_sdk_module fixture has already inserted the fake module.
# ---------------------------------------------------------------------------


def _sdk_type(name: str) -> type:
    """Return a class from the fake claude_agent_sdk module by name."""
    return getattr(sys.modules["claude_agent_sdk"], name)  # type: ignore[return-value]


def _real_text_block(text: str) -> Any:
    """Build a TextBlock whose isinstance check passes against the fake SDK."""
    obj = object.__new__(_sdk_type("TextBlock"))
    obj.text = text  # type: ignore[attr-defined]
    return obj


def _real_assistant_message(*blocks: Any) -> Any:
    """Build an AssistantMessage whose isinstance check passes."""
    obj = object.__new__(_sdk_type("AssistantMessage"))
    obj.content = list(blocks)  # type: ignore[attr-defined]
    return obj


def _real_result_message(
    *,
    session_id: str = "sess-mock-001",
    total_cost_usd: float = 0.0,
    num_turns: int = 1,
    duration_ms: int = 100,
    is_error: bool = False,
    result: str | None = None,
) -> Any:
    """Build a ResultMessage whose isinstance check passes."""
    obj = object.__new__(_sdk_type("ResultMessage"))
    obj.session_id = session_id  # type: ignore[attr-defined]
    obj.total_cost_usd = total_cost_usd  # type: ignore[attr-defined]
    obj.num_turns = num_turns  # type: ignore[attr-defined]
    obj.duration_ms = duration_ms  # type: ignore[attr-defined]
    obj.is_error = is_error  # type: ignore[attr-defined]
    obj.result = result  # type: ignore[attr-defined]
    return obj


# ---------------------------------------------------------------------------
# Patch target: output style helper (avoids file-system dependency)
# ---------------------------------------------------------------------------

_OUTPUT_STYLE_PATCH = (
    "claude_mpm.services.agents.sdk_runtime.SDKAgentRunner._get_output_style_content"
)


# ---------------------------------------------------------------------------
# Test 1 - equivalent of test_simple_query_returns_result
# ---------------------------------------------------------------------------


class TestMockSimpleQueryReturnsResult:
    """Verify run() returns text containing '4' with is_error=False."""

    async def test_simple_query_returns_result(self) -> None:
        with patch(_OUTPUT_STYLE_PATCH, return_value=None):
            from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

            text_block = _real_text_block("The answer is 4.")
            assistant_msg = _real_assistant_message(text_block)
            result_msg = _real_result_message(session_id="sess-test-1")

            async def _fake_query(prompt: str, options: Any):  # noqa: ANN401
                yield assistant_msg
                yield result_msg

            with patch("claude_mpm.services.agents.sdk_runtime.sdk_query", _fake_query):
                runner = SDKAgentRunner(
                    system_prompt="You are a concise math assistant. Answer with just the number.",
                    max_turns=2,
                )
                result = await runner.run("What is 2+2?")

        assert result.text is not None
        assert "4" in result.text
        assert result.is_error is False


# ---------------------------------------------------------------------------
# Test 2 - equivalent of test_session_id_returned
# ---------------------------------------------------------------------------


class TestMockSessionIdReturned:
    """Verify run() returns a non-empty session_id string."""

    async def test_session_id_returned(self) -> None:
        with patch(_OUTPUT_STYLE_PATCH, return_value=None):
            from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

            expected_session_id = "sess-hello-mock-42"
            text_block = _real_text_block("Hello.")
            assistant_msg = _real_assistant_message(text_block)
            result_msg = _real_result_message(session_id=expected_session_id)

            async def _fake_query(prompt: str, options: Any):  # noqa: ANN401
                yield assistant_msg
                yield result_msg

            with patch("claude_mpm.services.agents.sdk_runtime.sdk_query", _fake_query):
                runner = SDKAgentRunner(
                    system_prompt="You are concise. One word answers only.",
                    max_turns=2,
                )
                result = await runner.run("Say hello.")

        assert result.session_id is not None
        assert isinstance(result.session_id, str)
        assert len(result.session_id) > 0
        assert result.session_id == expected_session_id


# ---------------------------------------------------------------------------
# Test 3 - equivalent of test_event_bridge_captures_events
# ---------------------------------------------------------------------------


class TestMockEventBridgeCapturesEvents:
    """Verify run_streaming() + SDKEventBridge captures text and result events."""

    async def test_event_bridge_captures_events(self) -> None:
        with patch(_OUTPUT_STYLE_PATCH, return_value=None):
            from claude_mpm.services.agents.sdk_event_bridge import SDKEventBridge
            from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

            # Two text blocks so we get multiple text events
            block_a = _real_text_block("The answer is ")
            block_b = _real_text_block("4")
            assistant_msg = _real_assistant_message(block_a, block_b)
            result_msg = _real_result_message(
                session_id="sess-bridge-mock",
                num_turns=1,
                duration_ms=250,
            )

            async def _fake_query(prompt: str, options: Any):  # noqa: ANN401
                yield assistant_msg
                yield result_msg

            with patch("claude_mpm.services.agents.sdk_runtime.sdk_query", _fake_query):
                runner = SDKAgentRunner(
                    system_prompt="You are concise. Reply in one sentence.",
                    max_turns=2,
                )
                bridge = SDKEventBridge(agent_id="integration-test")

                result = await runner.run_streaming(
                    "What is 2+2? Just say the number.",
                    on_text=bridge.handle_text,
                    on_tool_call=bridge.handle_tool_call,
                )
                bridge.handle_result(result)

        # Should have at least one text event and one result event
        summary = bridge.summary()
        assert summary["total_events"] >= 2
        assert summary["agent_id"] == "integration-test"
        assert "result" in summary["event_counts"] or "error" in summary["event_counts"]

        # Verify the text events captured actual content
        text_events = [e for e in bridge.events if e.event_type == "text"]
        assert len(text_events) >= 1
        assert any("4" in e.data.get("text", "") for e in text_events)
