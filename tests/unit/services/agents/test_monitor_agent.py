"""Tests for MonitorAgent: session watchdog for SDK mode."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.monitor_agent import MonitorAgent, MonitorConfig

# ---------------------------------------------------------------------------
# MonitorConfig tests
# ---------------------------------------------------------------------------


class TestMonitorConfig:
    def test_default_config_values(self) -> None:
        cfg = MonitorConfig()
        assert cfg.token_limit == 200_000
        assert cfg.warn_thresholds == [70, 80, 90, 95]
        assert cfg.poll_interval == 10.0
        assert cfg.max_session_duration == 3600
        assert cfg.duration_warn_at == 0.8
        assert cfg.idle_timeout == 300
        assert cfg.auto_pause_threshold == 95

    def test_custom_config(self) -> None:
        cfg = MonitorConfig(
            token_limit=100_000,
            warn_thresholds=[50, 75],
            poll_interval=5.0,
            max_session_duration=1800,
            auto_pause_threshold=90,
        )
        assert cfg.token_limit == 100_000
        assert cfg.warn_thresholds == [50, 75]
        assert cfg.poll_interval == 5.0
        assert cfg.max_session_duration == 1800
        assert cfg.auto_pause_threshold == 90


# ---------------------------------------------------------------------------
# MonitorAgent lifecycle tests
# ---------------------------------------------------------------------------


class TestMonitorAgentLifecycle:
    def test_start_creates_background_thread(self) -> None:
        agent = MonitorAgent(MonitorConfig(poll_interval=0.05))
        assert not agent.is_running
        agent.start()
        try:
            assert agent.is_running
            assert agent._thread is not None
            assert agent._thread.daemon is True
            assert agent._thread.name == "mpm-monitor-agent"
        finally:
            agent.stop()

    def test_stop_terminates_thread(self) -> None:
        agent = MonitorAgent(MonitorConfig(poll_interval=0.05))
        agent.start()
        assert agent.is_running
        agent.stop()
        assert not agent.is_running
        assert agent._thread is None

    def test_is_running_property(self) -> None:
        agent = MonitorAgent()
        assert agent.is_running is False
        # Not started yet, thread is None
        agent._thread = None
        assert agent.is_running is False

    def test_double_start_warns(self) -> None:
        agent = MonitorAgent(MonitorConfig(poll_interval=0.05))
        agent.start()
        try:
            # Second start should be a no-op (logs warning)
            agent.start()
            assert agent.is_running
        finally:
            agent.stop()

    def test_get_status(self) -> None:
        agent = MonitorAgent(MonitorConfig(token_limit=100_000))
        status = agent.get_status()
        assert status["running"] is False
        assert status["warnings_sent"] == []
        assert status["config"]["token_limit"] == 100_000

    def test_get_status_with_warnings_sent(self) -> None:
        agent = MonitorAgent()
        agent._warnings_sent.add("context_70")
        agent._warnings_sent.add("duration_warning")
        status = agent.get_status()
        assert "context_70" in status["warnings_sent"]
        assert "duration_warning" in status["warnings_sent"]


# ---------------------------------------------------------------------------
# Helpers for health-check tests
# ---------------------------------------------------------------------------


def _make_state(
    *,
    state: str = "idle",
    tokens_used: int = 0,
    uptime_seconds: float = 0,
    last_activity: float | None = None,
) -> dict:
    """Build a fake session state dict."""
    return {
        "session_id": "test-session",
        "state": state,
        "model": "claude-sonnet-4",
        "started_at": time.time() - uptime_seconds,
        "turn_count": 1,
        "last_activity": last_activity if last_activity is not None else time.time(),
        "current_tool": None,
        "total_cost_usd": 0.0,
        "uptime_seconds": uptime_seconds,
        "context_usage": {"tokens_used": tokens_used},
    }


def _make_agent_with_mock_bus(
    config: MonitorConfig | None = None,
) -> tuple[MonitorAgent, MagicMock]:
    """Create a MonitorAgent with a mocked HookEventBus."""
    agent = MonitorAgent(config)
    mock_bus = MagicMock()
    agent._event_bus = mock_bus
    return agent, mock_bus


# ---------------------------------------------------------------------------
# Context pressure tests
# ---------------------------------------------------------------------------


class TestContextPressureChecks:
    def test_no_warning_below_threshold(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(tokens_used=100_000)  # 50%
        agent._check_context_pressure(state)
        mock_bus.send.assert_not_called()

    def test_warning_at_70_percent(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(tokens_used=140_000)  # 70%
        agent._check_context_pressure(state)
        mock_bus.send.assert_called_once()
        msg = mock_bus.send.call_args[0][0]
        assert msg.source == "monitor"
        assert "70%" in msg.text or "Monitoring" in msg.text

    def test_warning_at_80_percent_high_priority(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(tokens_used=160_000)  # 80%
        agent._check_context_pressure(state)
        # Should fire for 70 and 80
        assert mock_bus.send.call_count == 2
        texts = [call[0][0].text for call in mock_bus.send.call_args_list]
        assert any("wrapping up" in t.lower() for t in texts)

    def test_critical_at_95_percent(self) -> None:
        from claude_mpm.services.agents.hook_event_bus import MessagePriority

        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(tokens_used=190_000)  # 95%
        agent._check_context_pressure(state)
        # Should fire for 70, 80, 90, 95
        assert mock_bus.send.call_count == 4
        critical_msgs = [
            call[0][0]
            for call in mock_bus.send.call_args_list
            if call[0][0].priority == MessagePriority.CRITICAL
        ]
        assert len(critical_msgs) == 1
        assert "CRITICAL" in critical_msgs[0].text

    def test_warnings_not_repeated(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(tokens_used=140_000)  # 70%
        agent._check_context_pressure(state)
        assert mock_bus.send.call_count == 1

        # Second check at same level should not fire again
        mock_bus.reset_mock()
        agent._check_context_pressure(state)
        mock_bus.send.assert_not_called()

    def test_multiple_thresholds_fire_in_order(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        # Start at 70% -- fire threshold 70
        state70 = _make_state(tokens_used=140_000)
        agent._check_context_pressure(state70)
        assert mock_bus.send.call_count == 1

        # Jump to 90% -- fire 80 and 90 (70 already sent)
        mock_bus.reset_mock()
        state90 = _make_state(tokens_used=180_000)
        agent._check_context_pressure(state90)
        assert mock_bus.send.call_count == 2

    def test_no_warning_when_tokens_zero(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(tokens_used=0)
        agent._check_context_pressure(state)
        mock_bus.send.assert_not_called()


# ---------------------------------------------------------------------------
# Session duration tests
# ---------------------------------------------------------------------------


class TestSessionDurationChecks:
    def test_no_warning_before_threshold(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(uptime_seconds=100)  # well below 80% of 3600
        agent._check_session_duration(state)
        mock_bus.send.assert_not_called()

    def test_warning_at_duration_threshold(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        # 80% of 3600 = 2880s
        state = _make_state(uptime_seconds=2900)
        agent._check_session_duration(state)
        mock_bus.send.assert_called_once()
        msg = mock_bus.send.call_args[0][0]
        assert "minutes" in msg.text
        assert msg.source == "monitor"

    def test_duration_warning_not_repeated(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(uptime_seconds=3000)
        agent._check_session_duration(state)
        assert mock_bus.send.call_count == 1

        mock_bus.reset_mock()
        agent._check_session_duration(state)
        mock_bus.send.assert_not_called()


# ---------------------------------------------------------------------------
# Idle detection tests
# ---------------------------------------------------------------------------


class TestIdleDetection:
    def test_no_warning_when_idle_state(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        # state is "idle" not "processing" -- should skip
        state = _make_state(state="idle", last_activity=time.time() - 600)
        agent._check_idle_too_long(state)
        mock_bus.send.assert_not_called()

    def test_no_warning_when_recently_active(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(state="processing", last_activity=time.time() - 10)
        agent._check_idle_too_long(state)
        mock_bus.send.assert_not_called()

    def test_warning_when_processing_too_long(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(
            state="processing", last_activity=time.time() - 400
        )  # > 300s default
        agent._check_idle_too_long(state)
        mock_bus.send.assert_called_once()
        msg = mock_bus.send.call_args[0][0]
        assert "stuck" in msg.text.lower()

    def test_idle_warning_not_repeated(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        state = _make_state(state="processing", last_activity=time.time() - 400)
        agent._check_idle_too_long(state)
        assert mock_bus.send.call_count == 1

        mock_bus.reset_mock()
        agent._check_idle_too_long(state)
        mock_bus.send.assert_not_called()


# ---------------------------------------------------------------------------
# Message injection tests
# ---------------------------------------------------------------------------


class TestMessageInjection:
    def test_inject_sends_to_hook_event_bus(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        agent._inject_message("test alert", priority="normal")
        mock_bus.send.assert_called_once()

    def test_inject_with_correct_source_and_priority(self) -> None:
        from claude_mpm.services.agents.hook_event_bus import MessagePriority

        agent, mock_bus = _make_agent_with_mock_bus()
        agent._inject_message("critical alert", priority="critical")
        msg = mock_bus.send.call_args[0][0]
        assert msg.source == "monitor"
        assert msg.priority == MessagePriority.CRITICAL

    def test_inject_creates_event_bus_lazily(self) -> None:
        """Event bus is created on first inject if not pre-set."""
        agent = MonitorAgent()
        assert agent._event_bus is None
        with patch("claude_mpm.services.agents.hook_event_bus.HookEventBus") as MockBus:
            mock_instance = MagicMock()
            MockBus.return_value = mock_instance
            agent._inject_message("hello")
            MockBus.assert_called_once()
            mock_instance.send.assert_called_once()


# ---------------------------------------------------------------------------
# Full _check_session_health integration
# ---------------------------------------------------------------------------


class TestCheckSessionHealth:
    def test_skips_when_tracker_is_none(self) -> None:
        """No crash when global tracker is not set."""
        agent = MonitorAgent()
        with patch(
            "claude_mpm.services.agents.session_state_tracker.get_global_tracker",
            return_value=None,
        ):
            agent._check_session_health()  # should not raise

    def test_skips_when_state_is_stopped(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        mock_tracker = MagicMock()
        mock_tracker.get_session_state.return_value = _make_state(state="stopped")
        with patch(
            "claude_mpm.services.agents.session_state_tracker.get_global_tracker",
            return_value=mock_tracker,
        ):
            agent._check_session_health()
        mock_bus.send.assert_not_called()

    def test_skips_when_state_is_starting(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        mock_tracker = MagicMock()
        mock_tracker.get_session_state.return_value = _make_state(state="starting")
        with patch(
            "claude_mpm.services.agents.session_state_tracker.get_global_tracker",
            return_value=mock_tracker,
        ):
            agent._check_session_health()
        mock_bus.send.assert_not_called()

    def test_runs_checks_when_idle(self) -> None:
        agent, mock_bus = _make_agent_with_mock_bus()
        mock_tracker = MagicMock()
        mock_tracker.get_session_state.return_value = _make_state(
            state="idle", tokens_used=150_000, uptime_seconds=100
        )
        with patch(
            "claude_mpm.services.agents.session_state_tracker.get_global_tracker",
            return_value=mock_tracker,
        ):
            agent._check_session_health()
        # 75% tokens -> fires 70% threshold
        assert mock_bus.send.call_count == 1
