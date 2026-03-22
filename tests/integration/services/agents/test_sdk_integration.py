"""Integration tests for SDK runtime - requires claude-agent-sdk installed.

These tests actually call the SDK (not mocked) to verify end-to-end behavior.
Skip if SDK is not available or if running in CI without credentials.
"""

from __future__ import annotations

import os

import pytest

# Check SDK availability at import time
try:
    from claude_agent_sdk import ClaudeAgentOptions  # noqa: F401

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

HAS_API_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))

skip_no_sdk = pytest.mark.skipif(
    not SDK_AVAILABLE, reason="claude-agent-sdk not installed"
)
skip_no_key = pytest.mark.skipif(not HAS_API_KEY, reason="No ANTHROPIC_API_KEY set")


@skip_no_sdk
@skip_no_key
@pytest.mark.timeout(60)
class TestSDKIntegration:
    """End-to-end tests against the real SDK.

    These tests make actual API calls and incur cost.
    Use short prompts and max_turns=2 to keep costs low.
    """

    @pytest.mark.asyncio
    async def test_simple_query_returns_result(self) -> None:
        """Run a simple prompt and verify the result contains expected text."""
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner(
            system_prompt="You are a concise math assistant. Answer with just the number.",
            max_turns=2,
        )
        result = await runner.run("What is 2+2?")

        assert result.text is not None
        assert "4" in result.text
        assert result.is_error is False

    @pytest.mark.asyncio
    async def test_session_id_returned(self) -> None:
        """Verify that the SDK returns a session_id we can use for resume."""
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

        runner = SDKAgentRunner(
            system_prompt="You are concise. One word answers only.",
            max_turns=2,
        )
        result = await runner.run("Say hello.")

        assert result.session_id is not None
        assert isinstance(result.session_id, str)
        assert len(result.session_id) > 0

    @pytest.mark.asyncio
    async def test_event_bridge_captures_events(self) -> None:
        """Run with SDKEventBridge and verify events are captured."""
        from claude_mpm.services.agents.sdk_event_bridge import SDKEventBridge
        from claude_mpm.services.agents.sdk_runtime import SDKAgentRunner

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
