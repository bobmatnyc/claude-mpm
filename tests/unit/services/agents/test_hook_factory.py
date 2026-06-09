"""Tests for hook_factory — PreToolUse hook creation."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Awaitable
    from pathlib import Path

from claude_mpm.services.agents.hook_event_bus import (
    HookEventBus,
    HookMessage,
    MessagePriority,
)
from claude_mpm.services.agents.hook_factory import create_pretooluse_hook

# Serialize under pytest-xdist: tests share an asyncio event loop and
# JSONL queue files which can race when run across multiple workers.
pytestmark = pytest.mark.xdist_group("serial")


def _run(coro: Awaitable[Any]) -> Any:
    """Run a coroutine on a fresh event loop.

    Uses ``asyncio.run`` rather than ``asyncio.get_event_loop()`` so the
    tests do not depend on an ambient current event loop. In a broad test
    selection an earlier test that calls ``asyncio.run`` leaves the main
    thread's current loop set to ``None``; on Python 3.13
    ``get_event_loop()`` no longer auto-creates one and raises
    ``RuntimeError``, which made these tests order-dependent (see #712).
    """
    return asyncio.run(coro)


@pytest.fixture()
def bus(tmp_path: Path) -> HookEventBus:
    return HookEventBus(queue_path=tmp_path / "q.jsonl")


class TestPreToolUseHook:
    def test_returns_empty_when_no_messages(self, bus: HookEventBus) -> None:
        hook = create_pretooluse_hook(bus)
        result = _run(hook({}, None, {}))
        assert result == {}

    def test_returns_system_message_when_messages_pending(
        self, bus: HookEventBus
    ) -> None:
        bus.send(HookMessage(text="please check tests"))
        hook = create_pretooluse_hook(bus)
        result = _run(hook({}, None, {}))
        assert "systemMessage" in result
        assert "please check tests" in result["systemMessage"]

    def test_formats_source_prefix(self, bus: HookEventBus) -> None:
        bus.send(HookMessage(text="build failed", source="ci"))
        hook = create_pretooluse_hook(bus)
        result = _run(hook({}, "tool-123", {"signal": None}))
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
        result = _run(hook({}, None, {}))
        msg = result["systemMessage"]
        assert msg.startswith("CRITICAL")
        assert "[reviewer]" in msg
        assert "stop immediately" in msg

    def test_consumes_messages_so_next_call_empty(self, bus: HookEventBus) -> None:
        bus.send(HookMessage(text="one-shot"))
        hook = create_pretooluse_hook(bus)

        first = _run(hook({}, None, {}))
        assert "systemMessage" in first

        second = _run(hook({}, None, {}))
        assert second == {}
