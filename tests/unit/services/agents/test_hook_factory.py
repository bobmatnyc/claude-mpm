"""Tests for hook_factory — PreToolUse hook creation."""

from __future__ import annotations

import asyncio

import pytest

from claude_mpm.services.agents.hook_event_bus import (
    HookEventBus,
    HookMessage,
    MessagePriority,
)
from claude_mpm.services.agents.hook_factory import create_pretooluse_hook


@pytest.fixture()
def bus(tmp_path: pytest.TempPathFactory) -> HookEventBus:
    return HookEventBus(queue_path=tmp_path / "q.jsonl")


class TestPreToolUseHook:
    def test_returns_empty_when_no_messages(self, bus: HookEventBus) -> None:
        hook = create_pretooluse_hook(bus)
        result = asyncio.get_event_loop().run_until_complete(hook({}, None, {}))
        assert result == {}

    def test_returns_system_message_when_messages_pending(
        self, bus: HookEventBus
    ) -> None:
        bus.send(HookMessage(text="please check tests"))
        hook = create_pretooluse_hook(bus)
        result = asyncio.get_event_loop().run_until_complete(hook({}, None, {}))
        assert "systemMessage" in result
        assert "please check tests" in result["systemMessage"]

    def test_formats_source_prefix(self, bus: HookEventBus) -> None:
        bus.send(HookMessage(text="build failed", source="ci"))
        hook = create_pretooluse_hook(bus)
        result = asyncio.get_event_loop().run_until_complete(
            hook({}, "tool-123", {"signal": None})
        )
        assert "[ci]" in result["systemMessage"]

    def test_formats_critical_prefix(self, bus: HookEventBus) -> None:
        bus.send(
            HookMessage(
                text="stop immediately",
                priority=MessagePriority.CRITICAL,
                source="reviewer",
            )
        )
        hook = create_pretooluse_hook(bus)
        result = asyncio.get_event_loop().run_until_complete(hook({}, None, {}))
        msg = result["systemMessage"]
        assert msg.startswith("CRITICAL")
        assert "[reviewer]" in msg
        assert "stop immediately" in msg

    def test_consumes_messages_so_next_call_empty(self, bus: HookEventBus) -> None:
        bus.send(HookMessage(text="one-shot"))
        hook = create_pretooluse_hook(bus)

        first = asyncio.get_event_loop().run_until_complete(hook({}, None, {}))
        assert "systemMessage" in first

        second = asyncio.get_event_loop().run_until_complete(hook({}, None, {}))
        assert second == {}
