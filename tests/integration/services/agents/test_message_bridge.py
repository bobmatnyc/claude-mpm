"""End-to-end integration tests for the cross-project message bridge chain.

Verifies the full path:
    TaskInjector (mpm-message MCP send)
        -> MonitorAgent._check_incoming_messages() (poll)
        -> HookEventBus (queue)
        -> hook_factory pretooluse hook (consume_for_hook)
        -> {"systemMessage": ...} (PM session injection)

These tests use real instances (not mocks) wired together with temporary
directories so the chain executes exactly as it does in production.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from claude_mpm.services.agents.hook_event_bus import HookEventBus
from claude_mpm.services.agents.hook_factory import create_pretooluse_hook
from claude_mpm.services.agents.monitor_agent import MonitorAgent
from claude_mpm.services.communication.task_injector import TaskInjector

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def tasks_dir(tmp_path: Path) -> Path:
    """Temporary tasks directory for TaskInjector."""
    d = tmp_path / "tasks"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def queue_path(tmp_path: Path) -> Path:
    """Temporary queue file path for HookEventBus."""
    return tmp_path / "hook_messages.jsonl"


@pytest.fixture
def task_injector(tasks_dir: Path) -> TaskInjector:
    """Real TaskInjector pointing at a temp tasks directory."""
    return TaskInjector(tasks_dir=tasks_dir)


@pytest.fixture
def event_bus(queue_path: Path) -> HookEventBus:
    """Real HookEventBus pointing at a temp queue file."""
    return HookEventBus(queue_path=queue_path)


@pytest.fixture
def monitor_agent(task_injector: TaskInjector, event_bus: HookEventBus) -> MonitorAgent:
    """MonitorAgent wired to use the test injector and event bus."""
    agent = MonitorAgent()
    # Pre-inject the temp instances so MonitorAgent skips its lazy default init.
    agent._task_injector = task_injector
    agent._event_bus = event_bus
    return agent


def _run_pretooluse_hook(event_bus: HookEventBus) -> dict:
    """Invoke the async pretooluse hook synchronously and return its result."""
    hook = create_pretooluse_hook(event_bus)
    return asyncio.run(hook(input_data={}, tool_use_id=None, context=None))


# ----------------------------------------------------------------------
# Happy path
# ----------------------------------------------------------------------


def test_full_chain_injects_system_message(
    task_injector: TaskInjector,
    event_bus: HookEventBus,
    monitor_agent: MonitorAgent,
) -> None:
    """End-to-end: injected message flows to {"systemMessage": ...}."""
    # 1. Inject a message via TaskInjector (simulates mpm-message send)
    task_injector.inject_message_task(
        message_id="abc123",
        from_project="/tmp/project-a",
        subject="Implement OAuth2",
        body="Please add OAuth2 support with Google provider.",
        priority="high",
        from_agent="pm",
        message_type="task",
    )

    # 2. Trigger MonitorAgent's polling step.
    monitor_agent._check_incoming_messages()

    # 3. Verify the message was queued in the event bus.
    assert event_bus.queue_path.exists()
    queued = event_bus.queue_path.read_text().strip()
    assert queued, "expected event bus queue to contain at least one message"
    assert "Implement OAuth2" in queued

    # 4. Drive the hook factory output (what Claude Code actually receives).
    result = _run_pretooluse_hook(event_bus)

    # 5. The hook must return a systemMessage containing the injected text.
    assert "systemMessage" in result
    system_message = result["systemMessage"]
    assert isinstance(system_message, str)
    assert "Implement OAuth2" in system_message
    assert "project-a" in system_message  # rendered project name
    # The monitor tags messages with its source.
    assert "[monitor]" in system_message


# ----------------------------------------------------------------------
# Empty queue
# ----------------------------------------------------------------------


def test_empty_queue_returns_no_system_message(event_bus: HookEventBus) -> None:
    """consume_for_hook returns None and hook returns {} when queue is empty."""
    assert event_bus.consume_for_hook() is None

    result = _run_pretooluse_hook(event_bus)
    assert result == {}


def test_monitor_with_no_messages_does_not_queue(
    event_bus: HookEventBus, monitor_agent: MonitorAgent
) -> None:
    """MonitorAgent with empty task list does not enqueue anything."""
    monitor_agent._check_incoming_messages()

    # Either the queue file does not exist, or it's empty.
    if event_bus.queue_path.exists():
        assert event_bus.queue_path.read_text().strip() == ""

    result = _run_pretooluse_hook(event_bus)
    assert result == {}


# ----------------------------------------------------------------------
# Multiple messages
# ----------------------------------------------------------------------


def test_multiple_messages_consumed_in_one_call(
    task_injector: TaskInjector,
    event_bus: HookEventBus,
    monitor_agent: MonitorAgent,
) -> None:
    """All injected messages are surfaced in one systemMessage payload."""
    task_injector.inject_message_task(
        message_id="m1",
        from_project="/tmp/project-a",
        subject="First subject",
        body="First body",
        priority="high",
    )
    task_injector.inject_message_task(
        message_id="m2",
        from_project="/tmp/project-b",
        subject="Second subject",
        body="Second body",
        priority="normal",
    )
    task_injector.inject_message_task(
        message_id="m3",
        from_project="/tmp/project-c",
        subject="Third subject",
        body="Third body",
        priority="urgent",
    )

    monitor_agent._check_incoming_messages()

    result = _run_pretooluse_hook(event_bus)
    assert "systemMessage" in result
    system_message = result["systemMessage"]

    # All three subjects must appear in the single injected payload.
    assert "First subject" in system_message
    assert "Second subject" in system_message
    assert "Third subject" in system_message

    # After consumption the queue should be drained -- a follow-up hook call
    # must return an empty dict.
    follow_up = _run_pretooluse_hook(event_bus)
    assert follow_up == {}


def test_already_bridged_messages_not_redelivered(
    task_injector: TaskInjector,
    event_bus: HookEventBus,
    monitor_agent: MonitorAgent,
) -> None:
    """A second poll of the same task does not re-enqueue it."""
    task_injector.inject_message_task(
        message_id="dup-1",
        from_project="/tmp/project-a",
        subject="One-shot",
        body="Should be delivered once",
        priority="normal",
    )

    # First poll: enqueues and delivers.
    monitor_agent._check_incoming_messages()
    first = _run_pretooluse_hook(event_bus)
    assert "systemMessage" in first
    assert "One-shot" in first["systemMessage"]

    # Second poll: same task is still on disk, but already bridged.
    monitor_agent._check_incoming_messages()
    second = _run_pretooluse_hook(event_bus)
    assert second == {}
