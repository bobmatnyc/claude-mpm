"""Tests for OutputHandler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_mpm.commander.llm.summarizer import OutputSummarizer
from claude_mpm.commander.proxy.output_handler import OutputChunk, OutputHandler
from claude_mpm.commander.tmux_orchestrator import TmuxOrchestrator


class TestOutputChunk:
    """Test OutputChunk dataclass."""

    def test_output_chunk_creation(self):
        """Test creating an OutputChunk."""
        chunk = OutputChunk(
            instance_name="test-instance",
            raw_output="Test output",
            summary="Summary",
            is_complete=True,
        )

        assert chunk.instance_name == "test-instance"
        assert chunk.raw_output == "Test output"
        assert chunk.summary == "Summary"
        assert chunk.is_complete is True
        assert chunk.timestamp is not None

    def test_output_chunk_defaults(self):
        """Test OutputChunk default values."""
        chunk = OutputChunk(instance_name="test", raw_output="output")

        assert chunk.summary is None
        assert chunk.is_complete is False
        assert chunk.timestamp is not None


class TestOutputHandler:
    """Test OutputHandler."""

    def test_init(self):
        """Test initialization."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)
        mock_summarizer = MagicMock(spec=OutputSummarizer)

        handler = OutputHandler(mock_orchestrator, mock_summarizer)

        assert handler.orchestrator is mock_orchestrator
        assert handler.summarizer is mock_summarizer
        assert handler._output_buffers == {}
        assert handler._last_output_hash == {}

    def test_init_without_summarizer(self):
        """Test initialization without summarizer."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)

        handler = OutputHandler(mock_orchestrator)

        assert handler.orchestrator is mock_orchestrator
        assert handler.summarizer is None

    @pytest.mark.asyncio
    async def test_capture_output(self):
        """Test capturing output from pane."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)
        mock_orchestrator.capture_output.return_value = "Test output"

        handler = OutputHandler(mock_orchestrator)
        result = await handler.capture_output("%1", lines=50)

        assert result == "Test output"
        mock_orchestrator.capture_output.assert_called_once_with("%1", lines=50)

    @pytest.mark.asyncio
    async def test_get_new_output_first_capture(self):
        """Test get_new_output on first capture returns full output."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)
        mock_orchestrator.capture_output.return_value = "First output"

        handler = OutputHandler(mock_orchestrator)
        result = await handler.get_new_output("instance1", "%1")

        assert result == "First output"
        assert "instance1" in handler._last_output_hash

    @pytest.mark.asyncio
    async def test_get_new_output_no_change(self):
        """Test get_new_output when output hasn't changed."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)
        mock_orchestrator.capture_output.return_value = "Same output"

        handler = OutputHandler(mock_orchestrator)

        # First capture
        await handler.get_new_output("instance1", "%1")

        # Second capture - no change
        result = await handler.get_new_output("instance1", "%1")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_new_output_with_new_content(self):
        """Test get_new_output when new content is appended."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)

        handler = OutputHandler(mock_orchestrator)

        # First capture
        mock_orchestrator.capture_output.return_value = "Initial output"
        first = await handler.get_new_output("instance1", "%1")
        handler._output_buffers["instance1"] = first

        # Second capture - new content appended
        mock_orchestrator.capture_output.return_value = "Initial output\nNew line"
        second = await handler.get_new_output("instance1", "%1")

        assert second == "\nNew line"

    @pytest.mark.asyncio
    async def test_get_new_output_complete_change(self):
        """Test get_new_output when output completely changes."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)

        handler = OutputHandler(mock_orchestrator)

        # First capture
        mock_orchestrator.capture_output.return_value = "Initial output"
        first = await handler.get_new_output("instance1", "%1")
        handler._output_buffers["instance1"] = first

        # Second capture - completely different
        mock_orchestrator.capture_output.return_value = "Different output"
        second = await handler.get_new_output("instance1", "%1")

        assert second == "Different output"

    @pytest.mark.asyncio
    async def test_process_output_no_new_output(self):
        """Test process_output when there's no new output."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)
        mock_orchestrator.capture_output.return_value = "Same"

        handler = OutputHandler(mock_orchestrator)

        # First process
        await handler.process_output("instance1", "%1")

        # Second process - no change
        result = await handler.process_output("instance1", "%1")

        assert result is None

    @pytest.mark.asyncio
    async def test_process_output_with_new_output(self):
        """Test process_output with new output."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)

        handler = OutputHandler(mock_orchestrator)

        # Process output
        mock_orchestrator.capture_output.return_value = "Test output\n> "
        chunk = await handler.process_output("instance1", "%1")

        assert chunk is not None
        assert chunk.instance_name == "instance1"
        assert chunk.raw_output == "Test output\n> "
        assert chunk.summary is None
        assert chunk.is_complete is True  # Ends with "> "

    @pytest.mark.asyncio
    async def test_process_output_with_summarization(self):
        """Test process_output with summarization."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)
        mock_summarizer = MagicMock(spec=OutputSummarizer)
        mock_summarizer.needs_summarization.return_value = True
        mock_summarizer.summarize = AsyncMock(return_value="Summary of output")

        handler = OutputHandler(mock_orchestrator, mock_summarizer)

        # Process long output
        long_output = "x" * 1000
        mock_orchestrator.capture_output.return_value = long_output
        chunk = await handler.process_output("instance1", "%1", context="Test command")

        assert chunk is not None
        assert chunk.summary == "Summary of output"
        mock_summarizer.needs_summarization.assert_called_once_with(long_output)
        mock_summarizer.summarize.assert_called_once_with(long_output, "Test command")

    @pytest.mark.asyncio
    async def test_process_output_summarization_error(self):
        """Test process_output when summarization fails."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)
        mock_summarizer = MagicMock(spec=OutputSummarizer)
        mock_summarizer.needs_summarization.return_value = True
        mock_summarizer.summarize = AsyncMock(side_effect=Exception("API error"))

        handler = OutputHandler(mock_orchestrator, mock_summarizer)

        # Process output - should not raise despite summarization error
        mock_orchestrator.capture_output.return_value = "x" * 1000
        chunk = await handler.process_output("instance1", "%1")

        assert chunk is not None
        assert chunk.summary is None  # Summary failed but chunk still created

    def test_detect_completion_with_prompt(self):
        """Test completion detection with prompt."""
        handler = OutputHandler(MagicMock())

        assert handler.detect_completion("Some output\n> ") is True
        assert handler.detect_completion("Some output\n$ ") is True
        assert handler.detect_completion("Some output> ") is True

    def test_detect_completion_without_prompt(self):
        """Test completion detection without prompt."""
        handler = OutputHandler(MagicMock())

        assert handler.detect_completion("Some output") is False
        assert handler.detect_completion("Some output\n") is False
        assert handler.detect_completion("Partial >") is False

    def test_detect_completion_with_whitespace(self):
        """Test completion detection handles trailing whitespace."""
        handler = OutputHandler(MagicMock())

        assert handler.detect_completion("Some output\n>  \n") is True
        assert handler.detect_completion("Some output> \t") is True

    @pytest.mark.asyncio
    async def test_multiple_instances(self):
        """Test handling multiple instances independently."""
        mock_orchestrator = MagicMock(spec=TmuxOrchestrator)

        handler = OutputHandler(mock_orchestrator)

        # Instance 1
        mock_orchestrator.capture_output.return_value = "Instance 1 output"
        chunk1 = await handler.process_output("instance1", "%1")

        # Instance 2
        mock_orchestrator.capture_output.return_value = "Instance 2 output"
        chunk2 = await handler.process_output("instance2", "%2")

        assert chunk1.instance_name == "instance1"
        assert chunk2.instance_name == "instance2"
        assert chunk1.raw_output == "Instance 1 output"
        assert chunk2.raw_output == "Instance 2 output"

        # Verify separate buffers
        assert "instance1" in handler._output_buffers
        assert "instance2" in handler._output_buffers
