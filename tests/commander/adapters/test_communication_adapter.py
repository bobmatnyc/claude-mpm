"""Tests for ClaudeCodeCommunicationAdapter.

This module tests the async communication layer that manages I/O with
Claude Code via TmuxOrchestrator, using RuntimeAdapter for parsing.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from claude_mpm.commander.adapters import (
    AdapterState,
    ClaudeCodeAdapter,
    ClaudeCodeCommunicationAdapter,
    ParsedResponse,
)


class TestClaudeCodeCommunicationAdapter:
    """Test suite for ClaudeCodeCommunicationAdapter."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock TmuxOrchestrator."""
        orchestrator = Mock()
        orchestrator.send_keys = Mock()
        orchestrator.capture_output = Mock(return_value="")
        return orchestrator

    @pytest.fixture
    def mock_runtime_adapter(self):
        """Create mock RuntimeAdapter."""
        adapter = Mock(spec=ClaudeCodeAdapter)
        adapter.format_input = Mock(side_effect=lambda x: x.strip())
        adapter.parse_response = Mock(
            return_value=ParsedResponse(
                content="",
                is_complete=False,
                is_error=False,
                is_question=False,
            )
        )
        return adapter

    @pytest.fixture
    def adapter(self, mock_orchestrator, mock_runtime_adapter):
        """Create ClaudeCodeCommunicationAdapter instance."""
        return ClaudeCodeCommunicationAdapter(
            orchestrator=mock_orchestrator,
            pane_target="%0",
            runtime_adapter=mock_runtime_adapter,
            poll_interval=0.01,  # Fast polling for tests
        )

    # Initialization tests
    def test_init(self, mock_orchestrator, mock_runtime_adapter):
        """Test adapter initialization."""
        adapter = ClaudeCodeCommunicationAdapter(
            orchestrator=mock_orchestrator,
            pane_target="%0",
            runtime_adapter=mock_runtime_adapter,
        )

        assert adapter.orchestrator is mock_orchestrator
        assert adapter.pane_target == "%0"
        assert adapter.runtime_adapter is mock_runtime_adapter
        assert adapter.poll_interval == 0.2  # Default
        assert adapter._state == AdapterState.IDLE
        assert adapter._last_output == ""
        assert adapter._output_buffer == ""

    def test_init_custom_poll_interval(self, mock_orchestrator, mock_runtime_adapter):
        """Test adapter initialization with custom poll interval."""
        adapter = ClaudeCodeCommunicationAdapter(
            orchestrator=mock_orchestrator,
            pane_target="%1",
            runtime_adapter=mock_runtime_adapter,
            poll_interval=0.5,
        )

        assert adapter.poll_interval == 0.5
        assert adapter.pane_target == "%1"

    # is_ready tests
    def test_is_ready_when_idle(self, adapter):
        """Test is_ready returns True when state is IDLE."""
        adapter._state = AdapterState.IDLE
        assert adapter.is_ready() is True

    def test_is_ready_when_processing(self, adapter):
        """Test is_ready returns False when state is PROCESSING."""
        adapter._state = AdapterState.PROCESSING
        assert adapter.is_ready() is False

    def test_is_ready_when_waiting(self, adapter):
        """Test is_ready returns False when state is WAITING."""
        adapter._state = AdapterState.WAITING
        assert adapter.is_ready() is False

    def test_is_ready_when_error(self, adapter):
        """Test is_ready returns False when state is ERROR."""
        adapter._state = AdapterState.ERROR
        assert adapter.is_ready() is False

    # send tests
    @pytest.mark.asyncio
    async def test_send_formats_and_sends_message(
        self, adapter, mock_orchestrator, mock_runtime_adapter
    ):
        """Test send formats message and sends via tmux."""
        await adapter.send("Fix the bug in main.py")

        # Should format input
        mock_runtime_adapter.format_input.assert_called_once_with(
            "Fix the bug in main.py"
        )

        # Should send via orchestrator
        mock_orchestrator.send_keys.assert_called_once_with(
            "%0", "Fix the bug in main.py", enter=True
        )

        # Should update state
        assert adapter._state == AdapterState.PROCESSING
        assert adapter._output_buffer == ""

    @pytest.mark.asyncio
    async def test_send_strips_whitespace(self, adapter, mock_orchestrator):
        """Test send strips whitespace from message."""
        await adapter.send("  Fix the bug  ")

        # RuntimeAdapter.format_input strips whitespace
        mock_orchestrator.send_keys.assert_called_once_with(
            "%0", "Fix the bug", enter=True
        )

    # interrupt tests
    @pytest.mark.asyncio
    async def test_interrupt_sends_ctrl_c(self, adapter, mock_orchestrator):
        """Test interrupt sends Ctrl+C to tmux pane."""
        adapter._state = AdapterState.PROCESSING

        result = await adapter.interrupt()

        assert result is True
        mock_orchestrator.send_keys.assert_called_once_with("%0", "C-c", enter=False)
        assert adapter._state == AdapterState.IDLE

    @pytest.mark.asyncio
    async def test_interrupt_handles_exception(self, adapter, mock_orchestrator):
        """Test interrupt returns False on exception."""
        mock_orchestrator.send_keys.side_effect = Exception("tmux error")

        result = await adapter.interrupt()

        assert result is False

    # receive tests
    @pytest.mark.asyncio
    async def test_receive_returns_when_complete(
        self, adapter, mock_orchestrator, mock_runtime_adapter
    ):
        """Test receive returns AdapterResponse when idle detected."""
        # Setup: orchestrator returns output with prompt
        mock_orchestrator.capture_output.return_value = "File created: test.py\n> "

        # Setup: runtime adapter detects idle state
        mock_runtime_adapter.parse_response.return_value = ParsedResponse(
            content="File created: test.py",
            is_complete=True,
            is_error=False,
            is_question=False,
        )

        response = await adapter.receive(timeout=1.0)

        assert response.content == "File created: test.py"
        assert response.state == AdapterState.IDLE
        assert response.is_complete is True
        assert adapter._state == AdapterState.IDLE

    @pytest.mark.asyncio
    async def test_receive_detects_error(
        self, adapter, mock_orchestrator, mock_runtime_adapter
    ):
        """Test receive detects error state."""
        mock_orchestrator.capture_output.return_value = "Error: File not found\n> "

        mock_runtime_adapter.parse_response.return_value = ParsedResponse(
            content="Error: File not found",
            is_complete=True,
            is_error=True,
            error_message="Error: File not found",
            is_question=False,
        )

        response = await adapter.receive(timeout=1.0)

        assert response.is_complete is True
        assert adapter._state == AdapterState.ERROR

    @pytest.mark.asyncio
    async def test_receive_detects_question(
        self, adapter, mock_orchestrator, mock_runtime_adapter
    ):
        """Test receive detects question state."""
        mock_orchestrator.capture_output.return_value = "Should I proceed? (y/n)?"

        mock_runtime_adapter.parse_response.return_value = ParsedResponse(
            content="Should I proceed? (y/n)?",
            is_complete=False,
            is_error=False,
            is_question=True,
            question_text="Should I proceed? (y/n)?",
        )

        response = await adapter.receive(timeout=1.0)

        assert response.is_complete is False
        assert adapter._state == AdapterState.WAITING

    @pytest.mark.asyncio
    async def test_receive_timeout(
        self, adapter, mock_orchestrator, mock_runtime_adapter
    ):
        """Test receive returns partial response on timeout."""
        # Setup: never returns complete response
        mock_orchestrator.capture_output.return_value = "Processing..."
        mock_runtime_adapter.parse_response.return_value = ParsedResponse(
            content="Processing...",
            is_complete=False,
            is_error=False,
            is_question=False,
        )

        response = await adapter.receive(timeout=0.1)

        assert response.is_complete is False

    @pytest.mark.asyncio
    async def test_receive_accumulates_output(
        self, adapter, mock_orchestrator, mock_runtime_adapter
    ):
        """Test receive accumulates output over multiple captures."""
        # Simulate incremental output
        outputs = [
            "Starting task...",
            "Starting task...\nProcessing...",
            "Starting task...\nProcessing...\nDone!\n> ",
        ]
        call_count = [0]

        def capture_side_effect(*args, **kwargs):
            output = outputs[min(call_count[0], len(outputs) - 1)]
            call_count[0] += 1
            return output

        mock_orchestrator.capture_output.side_effect = capture_side_effect

        # Return complete on third call
        def parse_side_effect(output):
            if "Done!" in output:
                return ParsedResponse(
                    content=output,
                    is_complete=True,
                    is_error=False,
                    is_question=False,
                )
            return ParsedResponse(
                content=output,
                is_complete=False,
                is_error=False,
                is_question=False,
            )

        mock_runtime_adapter.parse_response.side_effect = parse_side_effect

        response = await adapter.receive(timeout=1.0)

        assert response.is_complete is True
        assert "Done!" in adapter._output_buffer

    # stream_response tests
    @pytest.mark.asyncio
    async def test_stream_response_yields_chunks(
        self, adapter, mock_orchestrator, mock_runtime_adapter
    ):
        """Test stream_response yields chunks as they arrive."""
        # Simulate incremental output
        outputs = [
            "Starting...",
            "Starting...\nProcessing...",
            "Starting...\nProcessing...\nDone!\n> ",
        ]
        call_count = [0]

        def capture_side_effect(*args, **kwargs):
            output = outputs[min(call_count[0], len(outputs) - 1)]
            call_count[0] += 1
            return output

        mock_orchestrator.capture_output.side_effect = capture_side_effect

        # Return complete on third call
        def parse_side_effect(output):
            if "Done!" in output:
                return ParsedResponse(
                    content=output,
                    is_complete=True,
                    is_error=False,
                    is_question=False,
                )
            return ParsedResponse(
                content=output,
                is_complete=False,
                is_error=False,
                is_question=False,
            )

        mock_runtime_adapter.parse_response.side_effect = parse_side_effect

        # Start streaming
        adapter._state = AdapterState.PROCESSING
        chunks = []
        async for chunk in adapter.stream_response():
            chunks.append(chunk)

        # Should yield incremental chunks
        assert len(chunks) > 0
        assert adapter._state == AdapterState.IDLE

    @pytest.mark.asyncio
    async def test_stream_response_stops_on_complete(
        self, adapter, mock_orchestrator, mock_runtime_adapter
    ):
        """Test stream_response stops when response is complete."""
        mock_orchestrator.capture_output.return_value = "Done!\n> "
        mock_runtime_adapter.parse_response.return_value = ParsedResponse(
            content="Done!",
            is_complete=True,
            is_error=False,
            is_question=False,
        )

        adapter._state = AdapterState.PROCESSING
        chunks = []

        async for chunk in adapter.stream_response():
            chunks.append(chunk)

        # Should stop streaming
        assert adapter._state == AdapterState.IDLE

    # _get_new_output tests
    def test_get_new_output_first_call(self, adapter):
        """Test _get_new_output on first call returns all output."""
        output = "New output"
        new = adapter._get_new_output(output)

        assert new == "New output"
        assert adapter._last_output == "New output"

    def test_get_new_output_incremental(self, adapter):
        """Test _get_new_output returns only new content."""
        adapter._last_output = "Previous output"
        output = "Previous output\nNew line"

        new = adapter._get_new_output(output)

        assert new == "\nNew line"
        assert adapter._last_output == "Previous output\nNew line"

    def test_get_new_output_no_change(self, adapter):
        """Test _get_new_output returns empty string when no change."""
        adapter._last_output = "Same output"
        output = "Same output"

        new = adapter._get_new_output(output)

        assert new == ""
        assert adapter._last_output == "Same output"

    def test_get_new_output_complete_replacement(self, adapter):
        """Test _get_new_output handles complete output replacement."""
        adapter._last_output = "Old output"
        output = "Completely different"

        new = adapter._get_new_output(output)

        assert new == "Completely different"
        assert adapter._last_output == "Completely different"
