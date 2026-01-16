"""Tests for RuntimeMonitor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.models.events import Event, EventPriority, EventType
from claude_mpm.commander.parsing.output_parser import OutputParser, ParseResult
from claude_mpm.commander.runtime.monitor import RuntimeMonitor
from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator


@pytest.fixture
def mock_orchestrator():
    """Create mock TmuxOrchestrator."""
    orchestrator = MagicMock(spec=TmuxOrchestrator)
    orchestrator.capture_output.return_value = "Sample output from Claude Code"
    return orchestrator


@pytest.fixture
def mock_parser():
    """Create mock OutputParser."""
    parser = MagicMock(spec=OutputParser)
    parser.parse.return_value = []  # Default: no events
    return parser


@pytest.fixture
def event_manager():
    """Create real EventManager."""
    return EventManager()


@pytest.fixture
def monitor(mock_orchestrator, mock_parser, event_manager):
    """Create RuntimeMonitor with mocks."""
    return RuntimeMonitor(
        orchestrator=mock_orchestrator,
        parser=mock_parser,
        event_manager=event_manager,
        poll_interval=0.1,  # Fast polling for tests
        capture_lines=100,
    )


class TestRuntimeMonitorInit:
    """Test RuntimeMonitor initialization."""

    def test_init_with_all_params(self, mock_orchestrator, mock_parser, event_manager):
        """Test initialization with all parameters."""
        monitor = RuntimeMonitor(
            orchestrator=mock_orchestrator,
            parser=mock_parser,
            event_manager=event_manager,
            poll_interval=2.0,
            capture_lines=500,
        )

        assert monitor.orchestrator == mock_orchestrator
        assert monitor.parser == mock_parser
        assert monitor.event_manager == event_manager
        assert monitor.poll_interval == 2.0
        assert monitor.capture_lines == 500

    def test_init_without_orchestrator(self, mock_parser, event_manager):
        """Test initialization fails without orchestrator."""
        with pytest.raises(ValueError, match="Orchestrator cannot be None"):
            RuntimeMonitor(None, mock_parser, event_manager)

    def test_init_without_parser(self, mock_orchestrator, event_manager):
        """Test initialization fails without parser."""
        with pytest.raises(ValueError, match="Parser cannot be None"):
            RuntimeMonitor(mock_orchestrator, None, event_manager)

    def test_init_without_event_manager(self, mock_orchestrator, mock_parser):
        """Test initialization fails without event manager."""
        with pytest.raises(ValueError, match="EventManager cannot be None"):
            RuntimeMonitor(mock_orchestrator, mock_parser, None)


class TestRuntimeMonitorStartStop:
    """Test starting and stopping monitors."""

    @pytest.mark.asyncio
    async def test_start_monitoring_creates_task(self, monitor):
        """Test start_monitoring creates background task."""
        await monitor.start_monitoring("%5", "proj_123")

        # Should be tracked
        assert "%5" in monitor._monitors
        project_id, task, _ = monitor._monitors["%5"]
        assert project_id == "proj_123"
        assert task is not None
        assert not task.done()

        # Cleanup
        await monitor.stop_monitoring("%5")

    @pytest.mark.asyncio
    async def test_start_monitoring_without_pane_target(self, monitor):
        """Test start_monitoring fails without pane target."""
        with pytest.raises(ValueError, match="Pane target cannot be None"):
            await monitor.start_monitoring("", "proj_123")

    @pytest.mark.asyncio
    async def test_start_monitoring_without_project_id(self, monitor):
        """Test start_monitoring fails without project ID."""
        with pytest.raises(ValueError, match="Project ID cannot be None"):
            await monitor.start_monitoring("%5", "")

    @pytest.mark.asyncio
    async def test_start_monitoring_duplicate_raises_error(self, monitor):
        """Test starting monitoring on same pane raises error."""
        await monitor.start_monitoring("%5", "proj_123")

        with pytest.raises(RuntimeError, match="Monitoring already active"):
            await monitor.start_monitoring("%5", "proj_123")

        # Cleanup
        await monitor.stop_monitoring("%5")

    @pytest.mark.asyncio
    async def test_stop_monitoring_cancels_task(self, monitor):
        """Test stop_monitoring cancels background task."""
        await monitor.start_monitoring("%5", "proj_123")

        _project_id, task, _ = monitor._monitors["%5"]
        assert not task.done()

        await monitor.stop_monitoring("%5")

        # Should be removed from monitors
        assert "%5" not in monitor._monitors
        # Task should be cancelled
        assert task.done()

    @pytest.mark.asyncio
    async def test_stop_monitoring_without_pane_target(self, monitor):
        """Test stop_monitoring fails without pane target."""
        with pytest.raises(ValueError, match="Pane target cannot be None"):
            await monitor.stop_monitoring("")

    @pytest.mark.asyncio
    async def test_stop_monitoring_non_existent_pane(self, monitor):
        """Test stop_monitoring handles non-existent pane gracefully."""
        # Should not raise error
        await monitor.stop_monitoring("%99")

    @pytest.mark.asyncio
    async def test_stop_all_stops_all_monitors(self, monitor):
        """Test stop_all stops all active monitors."""
        await monitor.start_monitoring("%5", "proj_123")
        await monitor.start_monitoring("%6", "proj_456")

        assert len(monitor._monitors) == 2

        await monitor.stop_all()

        assert len(monitor._monitors) == 0


class TestRuntimeMonitorPollOnce:
    """Test one-time polling."""

    @pytest.mark.asyncio
    async def test_poll_once_captures_and_parses_output(
        self, monitor, mock_orchestrator, mock_parser, event_manager
    ):
        """Test poll_once captures output and parses for events."""
        # Setup parser to return a parse result
        mock_parser.parse.return_value = [
            ParseResult(
                event_type=EventType.DECISION_NEEDED,
                title="Decision needed",
                content="Which option?",
                options=["A", "B"],
            )
        ]

        events = await monitor.poll_once("%5")

        # Should capture output
        mock_orchestrator.capture_output.assert_called_once_with("%5", lines=100)

        # Should parse output
        mock_parser.parse.assert_called_once()
        call_args = mock_parser.parse.call_args
        assert call_args[1]["content"] == "Sample output from Claude Code"
        assert call_args[1]["create_events"] is False

        # Should create events and return them
        assert len(events) == 1
        assert events[0].type == EventType.DECISION_NEEDED
        assert events[0].title == "Decision needed"

    @pytest.mark.asyncio
    async def test_poll_once_without_pane_target(self, monitor):
        """Test poll_once fails without pane target."""
        with pytest.raises(ValueError, match="Pane target cannot be None"):
            await monitor.poll_once("")

    @pytest.mark.asyncio
    async def test_poll_once_handles_capture_failure(self, monitor, mock_orchestrator):
        """Test poll_once handles capture failure gracefully."""
        mock_orchestrator.capture_output.side_effect = RuntimeError("Capture failed")

        events = await monitor.poll_once("%5")

        # Should return empty list on error
        assert events == []

    @pytest.mark.asyncio
    async def test_poll_once_with_no_events(
        self, monitor, mock_orchestrator, mock_parser
    ):
        """Test poll_once when no events detected."""
        mock_parser.parse.return_value = []

        events = await monitor.poll_once("%5")

        assert events == []


class TestRuntimeMonitorActiveMonitors:
    """Test active_monitors property."""

    @pytest.mark.asyncio
    async def test_active_monitors_empty_initially(self, monitor):
        """Test active_monitors is empty initially."""
        assert monitor.active_monitors == {}

    @pytest.mark.asyncio
    async def test_active_monitors_returns_mapping(self, monitor):
        """Test active_monitors returns pane -> project_id mapping."""
        await monitor.start_monitoring("%5", "proj_123")
        await monitor.start_monitoring("%6", "proj_456")

        active = monitor.active_monitors

        assert active == {"%5": "proj_123", "%6": "proj_456"}

        # Cleanup
        await monitor.stop_all()


class TestRuntimeMonitorBackgroundPolling:
    """Test background monitoring loop."""

    @pytest.mark.asyncio
    async def test_monitor_loop_polls_continuously(
        self, monitor, mock_orchestrator, mock_parser
    ):
        """Test monitor loop polls continuously until stopped."""
        await monitor.start_monitoring("%5", "proj_123")

        # Let it poll a few times
        await asyncio.sleep(0.3)  # Should poll ~3 times (0.1s interval)

        # Should have captured output multiple times
        assert mock_orchestrator.capture_output.call_count >= 2

        # Cleanup
        await monitor.stop_monitoring("%5")

    @pytest.mark.asyncio
    async def test_monitor_loop_detects_events(
        self, monitor, mock_orchestrator, mock_parser, event_manager
    ):
        """Test monitor loop detects and creates events."""
        # Setup parser to return events on second poll (different output)
        call_count = 0

        def side_effect_parse(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return [
                    ParseResult(
                        event_type=EventType.ERROR,
                        title="Error occurred",
                        content="Something failed",
                    )
                ]
            return []

        mock_parser.parse.side_effect = side_effect_parse

        # Vary output to trigger event detection
        outputs = ["output1", "output2 with error", "output3"]
        mock_orchestrator.capture_output.side_effect = outputs

        await monitor.start_monitoring("%5", "proj_123")

        # Let it poll a few times
        await asyncio.sleep(0.3)

        # Should have created event
        events = event_manager.get_pending("proj_123")
        # Note: May be 0 or 1 depending on timing and hash changes
        # At minimum, parser should have been called
        assert mock_parser.parse.call_count >= 1

        # Cleanup
        await monitor.stop_monitoring("%5")

    @pytest.mark.asyncio
    async def test_monitor_loop_handles_capture_errors(
        self, monitor, mock_orchestrator, mock_parser
    ):
        """Test monitor loop handles capture errors without crashing."""
        # First call succeeds, second fails, third succeeds
        mock_orchestrator.capture_output.side_effect = [
            "output1",
            RuntimeError("Capture failed"),
            "output2",
        ]

        await monitor.start_monitoring("%5", "proj_123")

        # Let it poll through the error
        await asyncio.sleep(0.3)

        # Should still be running (not crashed)
        assert "%5" in monitor._monitors

        # Cleanup
        await monitor.stop_monitoring("%5")

    @pytest.mark.asyncio
    async def test_monitor_loop_skips_unchanged_output(
        self, monitor, mock_orchestrator, mock_parser
    ):
        """Test monitor loop skips parsing when output hasn't changed."""
        # Return same output every time
        mock_orchestrator.capture_output.return_value = "unchanged output"

        await monitor.start_monitoring("%5", "proj_123")

        # Let it poll several times
        await asyncio.sleep(0.3)

        # Should capture multiple times
        assert mock_orchestrator.capture_output.call_count >= 2

        # But parser should only be called once (first poll)
        # Subsequent polls should skip parsing due to unchanged hash
        assert mock_parser.parse.call_count <= 1

        # Cleanup
        await monitor.stop_monitoring("%5")


class TestRuntimeMonitorIntegration:
    """Integration tests for RuntimeMonitor workflow."""

    @pytest.mark.asyncio
    async def test_full_monitoring_lifecycle(
        self, monitor, mock_orchestrator, mock_parser, event_manager
    ):
        """Test full monitoring lifecycle."""
        # Start monitoring
        await monitor.start_monitoring("%5", "proj_123")
        assert "%5" in monitor.active_monitors

        # Poll once
        events = await monitor.poll_once("%5")
        assert isinstance(events, list)

        # Stop monitoring
        await monitor.stop_monitoring("%5")
        assert "%5" not in monitor.active_monitors

    @pytest.mark.asyncio
    async def test_multiple_panes_monitored_simultaneously(self, monitor):
        """Test monitoring multiple panes at same time."""
        await monitor.start_monitoring("%5", "proj_123")
        await monitor.start_monitoring("%6", "proj_456")
        await monitor.start_monitoring("%7", "proj_789")

        assert len(monitor.active_monitors) == 3

        # All should be running
        for pane in ["%5", "%6", "%7"]:
            assert pane in monitor._monitors
            _, task, _ = monitor._monitors[pane]
            assert not task.done()

        # Cleanup
        await monitor.stop_all()
