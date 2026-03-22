"""Tests for HookEventBus file-based message queue."""

from __future__ import annotations

import json
import threading

import pytest  # noqa: TC002

from claude_mpm.services.agents.hook_event_bus import (
    HookEventBus,
    HookMessage,
    MessagePriority,
)

# -- HookMessage serialisation round-trip ------------------------------------


class TestHookMessageSerialization:
    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        msg = HookMessage(
            text="hello",
            priority=MessagePriority.HIGH,
            source="monitor",
            timestamp=1234567890.0,
            metadata={"key": "value"},
        )
        restored = HookMessage.from_dict(msg.to_dict())
        assert restored.text == msg.text
        assert restored.priority == msg.priority
        assert restored.source == msg.source
        assert restored.timestamp == msg.timestamp
        assert restored.metadata == msg.metadata

    def test_from_dict_defaults(self) -> None:
        msg = HookMessage.from_dict({"text": "bare minimum"})
        assert msg.text == "bare minimum"
        assert msg.priority == MessagePriority.NORMAL
        assert msg.source == "unknown"
        assert msg.metadata == {}


# -- Basic send / consume ----------------------------------------------------


class TestSendAndConsume:
    def test_send_and_consume(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        bus.send(HookMessage(text="msg-1"))
        bus.send(HookMessage(text="msg-2"))

        messages = bus.consume()
        assert len(messages) == 2
        assert messages[0].text == "msg-1"
        assert messages[1].text == "msg-2"

    def test_consume_clears_queue(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        bus.send(HookMessage(text="msg-1"))

        first = bus.consume()
        assert len(first) == 1

        second = bus.consume()
        assert second == []

    def test_empty_queue_returns_empty(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        assert bus.consume() == []

    def test_missing_file_returns_empty(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "nonexistent" / "q.jsonl")
        # Parent dir doesn't exist for consume (it is created in __init__
        # only for the direct parent).  consume should handle gracefully.
        bus.queue_path = tmp_path / "does_not_exist.jsonl"
        assert bus.consume() == []


# -- Priority sorting --------------------------------------------------------


class TestPrioritySorting:
    def test_priority_sorting(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        bus.send(HookMessage(text="low", priority=MessagePriority.LOW))
        bus.send(HookMessage(text="critical", priority=MessagePriority.CRITICAL))
        bus.send(HookMessage(text="normal", priority=MessagePriority.NORMAL))
        bus.send(HookMessage(text="high", priority=MessagePriority.HIGH))

        messages = bus.consume()
        priorities = [m.priority for m in messages]
        assert priorities == [
            MessagePriority.CRITICAL,
            MessagePriority.HIGH,
            MessagePriority.NORMAL,
            MessagePriority.LOW,
        ]

    def test_critical_always_injected(self, tmp_path: pytest.TempPathFactory) -> None:
        """Critical messages are never deferred regardless of tool-call count."""
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        bus.send(HookMessage(text="urgent", priority=MessagePriority.CRITICAL))

        # First tool call -- low-priority would be deferred, critical should not
        result = bus.consume_for_hook()
        assert result is not None
        assert "CRITICAL" in result
        assert "urgent" in result


# -- Concurrent writes -------------------------------------------------------


class TestConcurrentWrites:
    def test_concurrent_writes(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        errors: list[Exception] = []

        def writer(n: int) -> None:
            try:
                for i in range(20):
                    bus.send(HookMessage(text=f"w{n}-{i}"))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Writer threads raised errors: {errors}"

        messages = bus.consume()
        assert len(messages) == 80  # 4 writers x 20 messages


# -- Malformed JSON handling -------------------------------------------------


class TestMalformedJson:
    def test_malformed_json_skipped(self, tmp_path: pytest.TempPathFactory) -> None:
        queue_file = tmp_path / "q.jsonl"
        # Write a valid message then a corrupt line
        valid = json.dumps({"text": "good", "priority": "normal"})
        queue_file.write_text(f"{valid}\nNOT-JSON\n{valid}\n")

        bus = HookEventBus(queue_path=queue_file)
        messages = bus.consume()
        assert len(messages) == 2
        assert all(m.text == "good" for m in messages)


# -- consume_for_hook formatting ---------------------------------------------


class TestConsumeForHook:
    def test_returns_none_when_empty(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        assert bus.consume_for_hook() is None

    def test_returns_formatted_string(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        bus.send(HookMessage(text="check this", source="monitor"))
        result = bus.consume_for_hook()
        assert result is not None
        assert "[monitor]" in result
        assert "check this" in result

    def test_critical_prefix(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        bus.send(
            HookMessage(
                text="abort now",
                priority=MessagePriority.CRITICAL,
                source="ci",
            )
        )
        result = bus.consume_for_hook()
        assert result is not None
        assert result.startswith("CRITICAL")
        assert "[ci]" in result

    def test_unknown_source_no_prefix(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        bus.send(HookMessage(text="bare"))
        result = bus.consume_for_hook()
        assert result is not None
        assert result == "bare"


# -- Low-priority deferral ---------------------------------------------------


class TestLowPriorityDeferral:
    def test_low_priority_deferred(self, tmp_path: pytest.TempPathFactory) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        bus._low_priority_interval = 3

        bus.send(HookMessage(text="low-msg", priority=MessagePriority.LOW))

        # Tool calls 1 and 2: low-priority deferred
        result1 = bus.consume_for_hook()
        assert result1 is None  # deferred, nothing else to inject

        # The deferred message was re-queued; send nothing new
        result2 = bus.consume_for_hook()
        assert result2 is None

        # Tool call 3: interval hit, low-priority injected
        result3 = bus.consume_for_hook()
        assert result3 is not None
        assert "low-msg" in result3

    def test_mixed_priority_partial_inject(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        bus = HookEventBus(queue_path=tmp_path / "q.jsonl")
        bus._low_priority_interval = 5

        bus.send(HookMessage(text="normal-msg", priority=MessagePriority.NORMAL))
        bus.send(HookMessage(text="low-msg", priority=MessagePriority.LOW))

        # First call: normal injected, low deferred
        result = bus.consume_for_hook()
        assert result is not None
        assert "normal-msg" in result
        assert "low-msg" not in result

        # Low message was re-queued
        remaining = bus.consume()
        assert len(remaining) == 1
        assert remaining[0].text == "low-msg"
