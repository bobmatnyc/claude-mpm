"""Tests for OutputSummarizer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_mpm.commander.llm import OpenRouterClient, OutputSummarizer


class TestOutputSummarizer:
    """Test OutputSummarizer."""

    def test_init(self):
        """Test initialization with client."""
        mock_client = MagicMock(spec=OpenRouterClient)
        summarizer = OutputSummarizer(mock_client)
        assert summarizer.client is mock_client

    @pytest.mark.asyncio
    async def test_summarize_without_context(self):
        """Test summarization without context."""
        mock_client = MagicMock(spec=OpenRouterClient)
        mock_client.chat = AsyncMock(return_value="Concise summary")

        summarizer = OutputSummarizer(mock_client)
        output = "Long output from Claude Code " * 100

        result = await summarizer.summarize(output)

        assert result == "Concise summary"

        # Verify client was called with correct parameters
        mock_client.chat.assert_called_once()
        call_args = mock_client.chat.call_args

        # Check messages
        messages = call_args[0][0]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "Summarize" in messages[0]["content"]
        assert output in messages[0]["content"]
        assert "2-3 sentences" in messages[0]["content"]

        # Check system prompt
        system = call_args[1]["system"]
        assert "technical summarization" in system.lower()

    @pytest.mark.asyncio
    async def test_summarize_with_context(self):
        """Test summarization with context."""
        mock_client = MagicMock(spec=OpenRouterClient)
        mock_client.chat = AsyncMock(return_value="Summary with context")

        summarizer = OutputSummarizer(mock_client)
        output = "Long output from Claude Code " * 100
        context = "User requested file listing"

        result = await summarizer.summarize(output, context=context)

        assert result == "Summary with context"

        # Verify client was called with context
        mock_client.chat.assert_called_once()
        call_args = mock_client.chat.call_args

        messages = call_args[0][0]
        assert "Context: " + context in messages[0]["content"]
        assert output in messages[0]["content"]

        # Check for structured summary request
        assert "What action was taken" in messages[0]["content"]
        assert "key result or outcome" in messages[0]["content"]
        assert "warnings or next steps" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_summarize_propagates_exceptions(self):
        """Test that summarize propagates client exceptions."""
        mock_client = MagicMock(spec=OpenRouterClient)
        mock_client.chat = AsyncMock(side_effect=Exception("API error"))

        summarizer = OutputSummarizer(mock_client)

        with pytest.raises(Exception, match="API error"):
            await summarizer.summarize("Some output")

    def test_needs_summarization_below_threshold(self):
        """Test needs_summarization with short output."""
        mock_client = MagicMock(spec=OpenRouterClient)
        summarizer = OutputSummarizer(mock_client)

        short_output = "Short output"
        assert not summarizer.needs_summarization(short_output)
        assert not summarizer.needs_summarization(short_output, threshold=500)

    def test_needs_summarization_above_threshold(self):
        """Test needs_summarization with long output."""
        mock_client = MagicMock(spec=OpenRouterClient)
        summarizer = OutputSummarizer(mock_client)

        long_output = "x" * 1000
        assert summarizer.needs_summarization(long_output)
        assert summarizer.needs_summarization(long_output, threshold=500)

    def test_needs_summarization_at_threshold(self):
        """Test needs_summarization at exact threshold."""
        mock_client = MagicMock(spec=OpenRouterClient)
        summarizer = OutputSummarizer(mock_client)

        # Exactly at threshold should NOT need summarization
        at_threshold = "x" * 500
        assert not summarizer.needs_summarization(at_threshold, threshold=500)

        # Just over threshold SHOULD need summarization
        over_threshold = "x" * 501
        assert summarizer.needs_summarization(over_threshold, threshold=500)

    def test_needs_summarization_custom_threshold(self):
        """Test needs_summarization with custom threshold."""
        mock_client = MagicMock(spec=OpenRouterClient)
        summarizer = OutputSummarizer(mock_client)

        output = "x" * 250

        # Should need summarization with low threshold
        assert summarizer.needs_summarization(output, threshold=100)

        # Should NOT need summarization with high threshold
        assert not summarizer.needs_summarization(output, threshold=1000)

    def test_needs_summarization_empty_string(self):
        """Test needs_summarization with empty string."""
        mock_client = MagicMock(spec=OpenRouterClient)
        summarizer = OutputSummarizer(mock_client)

        assert not summarizer.needs_summarization("")
        assert not summarizer.needs_summarization("", threshold=0)

    @pytest.mark.asyncio
    async def test_integration_summarize_flow(self):
        """Test integration flow: check threshold, then summarize if needed."""
        mock_client = MagicMock(spec=OpenRouterClient)
        mock_client.chat = AsyncMock(return_value="Brief summary")

        summarizer = OutputSummarizer(mock_client)

        # Short output - no summarization needed
        short_output = "Brief output"
        if not summarizer.needs_summarization(short_output):
            result = short_output
        else:
            result = await summarizer.summarize(short_output)

        assert result == "Brief output"
        mock_client.chat.assert_not_called()

        # Long output - summarization needed
        long_output = "x" * 1000
        if summarizer.needs_summarization(long_output):
            result = await summarizer.summarize(long_output)
        else:
            result = long_output

        assert result == "Brief summary"
        mock_client.chat.assert_called_once()
