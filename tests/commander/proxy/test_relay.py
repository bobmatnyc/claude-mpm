"""Tests for OutputRelay."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_mpm.commander.proxy.formatter import OutputFormatter
from claude_mpm.commander.proxy.output_handler import OutputChunk, OutputHandler
from claude_mpm.commander.proxy.relay import OutputRelay


class TestOutputRelay:
    """Test OutputRelay."""

    def test_init(self):
        """Test initialization."""
        mock_handler = MagicMock(spec=OutputHandler)
        mock_formatter = MagicMock(spec=OutputFormatter)
        mock_callback = AsyncMock()

        relay = OutputRelay(mock_handler, mock_formatter, mock_callback)

        assert relay.handler is mock_handler
        assert relay.formatter is mock_formatter
        assert relay.on_output is mock_callback
        assert relay._monitoring == {}

    def test_init_without_callback(self):
        """Test initialization without callback."""
        mock_handler = MagicMock(spec=OutputHandler)
        mock_formatter = MagicMock(spec=OutputFormatter)

        relay = OutputRelay(mock_handler, mock_formatter)

        assert relay.on_output is None

    @pytest.mark.asyncio
    async def test_start_relay(self):
        """Test starting output relay."""
        mock_handler = MagicMock(spec=OutputHandler)
        mock_handler.process_output = AsyncMock(return_value=None)
        mock_formatter = MagicMock(spec=OutputFormatter)

        relay = OutputRelay(mock_handler, mock_formatter)

        # Start relay
        await relay.start_relay("instance1", "%1")

        # Verify task was created
        assert "instance1" in relay._monitoring
        assert isinstance(relay._monitoring["instance1"], asyncio.Task)

        # Stop relay
        await relay.stop_relay("instance1")

    @pytest.mark.asyncio
    async def test_start_relay_replaces_existing(self):
        """Test starting relay replaces existing one."""
        mock_handler = MagicMock(spec=OutputHandler)
        mock_handler.process_output = AsyncMock(return_value=None)
        mock_formatter = MagicMock(spec=OutputFormatter)

        relay = OutputRelay(mock_handler, mock_formatter)

        # Start first relay
        await relay.start_relay("instance1", "%1")
        first_task = relay._monitoring["instance1"]

        # Start second relay for same instance
        await relay.start_relay("instance1", "%1")
        second_task = relay._monitoring["instance1"]

        # Should be different task
        assert first_task is not second_task
        assert first_task.cancelled()

        # Cleanup
        await relay.stop_relay("instance1")

    @pytest.mark.asyncio
    async def test_stop_relay(self):
        """Test stopping output relay."""
        mock_handler = MagicMock(spec=OutputHandler)
        mock_handler.process_output = AsyncMock(return_value=None)
        mock_formatter = MagicMock(spec=OutputFormatter)

        relay = OutputRelay(mock_handler, mock_formatter)

        # Start and stop
        await relay.start_relay("instance1", "%1")
        await relay.stop_relay("instance1")

        # Verify task was removed and cancelled
        assert "instance1" not in relay._monitoring

    @pytest.mark.asyncio
    async def test_stop_relay_nonexistent(self):
        """Test stopping nonexistent relay."""
        mock_handler = MagicMock(spec=OutputHandler)
        mock_formatter = MagicMock(spec=OutputFormatter)

        relay = OutputRelay(mock_handler, mock_formatter)

        # Should not raise
        await relay.stop_relay("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_all(self):
        """Test stopping all relays."""
        mock_handler = MagicMock(spec=OutputHandler)
        mock_handler.process_output = AsyncMock(return_value=None)
        mock_formatter = MagicMock(spec=OutputFormatter)

        relay = OutputRelay(mock_handler, mock_formatter)

        # Start multiple relays
        await relay.start_relay("instance1", "%1")
        await relay.start_relay("instance2", "%2")
        await relay.start_relay("instance3", "%3")

        # Stop all
        await relay.stop_all()

        # Verify all stopped
        assert len(relay._monitoring) == 0

    @pytest.mark.asyncio
    async def test_monitor_output_calls_callback(self):
        """Test monitor output calls callback with formatted output."""
        mock_handler = MagicMock(spec=OutputHandler)
        chunk = OutputChunk(
            instance_name="instance1", raw_output="Test output", is_complete=True
        )
        # Return chunk once, then None repeatedly
        call_count = 0

        async def process_output_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return chunk if call_count == 1 else None

        mock_handler.process_output = AsyncMock(side_effect=process_output_side_effect)

        mock_formatter = MagicMock(spec=OutputFormatter)
        mock_formatter.format_raw.return_value = "Formatted raw output"

        mock_callback = AsyncMock()

        relay = OutputRelay(mock_handler, mock_formatter, mock_callback)

        # Start relay with very short interval
        await relay.start_relay("instance1", "%1", poll_interval=0.01)

        # Wait for callback
        await asyncio.sleep(0.05)

        # Stop relay
        await relay.stop_relay("instance1")

        # Verify callback was called
        assert mock_callback.called
        mock_callback.assert_called_with("Formatted raw output")

    @pytest.mark.asyncio
    async def test_monitor_output_uses_summary_format(self):
        """Test monitor prefers summary format when available."""
        mock_handler = MagicMock(spec=OutputHandler)
        chunk = OutputChunk(
            instance_name="instance1",
            raw_output="Long output",
            summary="Summary",
            is_complete=True,
        )
        # Return chunk once, then None repeatedly
        call_count = 0

        async def process_output_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return chunk if call_count == 1 else None

        mock_handler.process_output = AsyncMock(side_effect=process_output_side_effect)

        mock_formatter = MagicMock(spec=OutputFormatter)
        mock_formatter.format_summary.return_value = "Formatted summary"

        mock_callback = AsyncMock()

        relay = OutputRelay(mock_handler, mock_formatter, mock_callback)

        # Start relay
        await relay.start_relay("instance1", "%1", poll_interval=0.01)

        # Wait for callback
        await asyncio.sleep(0.05)

        # Stop relay
        await relay.stop_relay("instance1")

        # Verify summary format was used
        mock_formatter.format_summary.assert_called_once()
        mock_callback.assert_called_with("Formatted summary")

    @pytest.mark.asyncio
    async def test_monitor_output_handles_exceptions(self):
        """Test monitor handles exceptions gracefully."""
        mock_handler = MagicMock(spec=OutputHandler)
        mock_handler.process_output = AsyncMock(side_effect=Exception("Test error"))

        mock_formatter = MagicMock(spec=OutputFormatter)
        mock_formatter.format_error.return_value = "Formatted error"

        mock_callback = AsyncMock()

        relay = OutputRelay(mock_handler, mock_formatter, mock_callback)

        # Start relay
        await relay.start_relay("instance1", "%1", poll_interval=0.01)

        # Wait for error
        await asyncio.sleep(0.05)

        # Task should have raised but been captured
        task = relay._monitoring.get("instance1")
        if task:
            with pytest.raises(Exception, match="Test error"):
                await task

    @pytest.mark.asyncio
    async def test_monitor_output_no_callback(self):
        """Test monitor works without callback."""
        mock_handler = MagicMock(spec=OutputHandler)
        chunk = OutputChunk(instance_name="instance1", raw_output="Test")
        # Return chunk once, then None repeatedly
        call_count = 0

        async def process_output_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return chunk if call_count == 1 else None

        mock_handler.process_output = AsyncMock(side_effect=process_output_side_effect)

        mock_formatter = MagicMock(spec=OutputFormatter)

        # No callback
        relay = OutputRelay(mock_handler, mock_formatter)

        # Start relay
        await relay.start_relay("instance1", "%1", poll_interval=0.01)

        # Wait a bit
        await asyncio.sleep(0.05)

        # Stop relay
        await relay.stop_relay("instance1")

        # Should not crash despite no callback

    @pytest.mark.asyncio
    async def test_get_latest_output_with_new_output(self):
        """Test getting latest output."""
        mock_handler = MagicMock(spec=OutputHandler)
        chunk = OutputChunk(
            instance_name="instance1", raw_output="Latest output", is_complete=True
        )
        mock_handler.process_output = AsyncMock(return_value=chunk)

        mock_formatter = MagicMock(spec=OutputFormatter)
        mock_formatter.format_raw.return_value = "Formatted latest"

        relay = OutputRelay(mock_handler, mock_formatter)

        result = await relay.get_latest_output("instance1", "%1")

        assert result == "Formatted latest"
        mock_handler.process_output.assert_called_once_with(
            "instance1", "%1", context=None
        )

    @pytest.mark.asyncio
    async def test_get_latest_output_with_context(self):
        """Test getting latest output with context."""
        mock_handler = MagicMock(spec=OutputHandler)
        chunk = OutputChunk(
            instance_name="instance1", raw_output="Output", summary="Summary"
        )
        mock_handler.process_output = AsyncMock(return_value=chunk)

        mock_formatter = MagicMock(spec=OutputFormatter)
        mock_formatter.format_summary.return_value = "Formatted with summary"

        relay = OutputRelay(mock_handler, mock_formatter)

        result = await relay.get_latest_output("instance1", "%1", context="test cmd")

        assert result == "Formatted with summary"
        mock_handler.process_output.assert_called_once_with(
            "instance1", "%1", context="test cmd"
        )

    @pytest.mark.asyncio
    async def test_get_latest_output_no_new_output(self):
        """Test getting latest output when there's no new output."""
        mock_handler = MagicMock(spec=OutputHandler)
        mock_handler.process_output = AsyncMock(return_value=None)

        mock_formatter = MagicMock(spec=OutputFormatter)
        mock_formatter.format_status.return_value = "No new output"

        relay = OutputRelay(mock_handler, mock_formatter)

        result = await relay.get_latest_output("instance1", "%1")

        assert result == "No new output"
        mock_formatter.format_status.assert_called_once_with(
            "instance1", "No new output"
        )

    @pytest.mark.asyncio
    async def test_multiple_relays_independent(self):
        """Test multiple relays run independently."""
        mock_handler = MagicMock(spec=OutputHandler)
        mock_handler.process_output = AsyncMock(return_value=None)
        mock_formatter = MagicMock(spec=OutputFormatter)

        relay = OutputRelay(mock_handler, mock_formatter)

        # Start multiple relays
        await relay.start_relay("instance1", "%1", poll_interval=0.01)
        await relay.start_relay("instance2", "%2", poll_interval=0.01)

        # Verify both running
        assert len(relay._monitoring) == 2
        assert "instance1" in relay._monitoring
        assert "instance2" in relay._monitoring

        # Stop one
        await relay.stop_relay("instance1")

        # Verify only one stopped
        assert len(relay._monitoring) == 1
        assert "instance2" in relay._monitoring

        # Cleanup
        await relay.stop_all()
