"""Tests for OutputFormatter."""

from claude_mpm.commander.proxy.formatter import OutputFormatter
from claude_mpm.commander.proxy.output_handler import OutputChunk


class TestOutputFormatter:
    """Test OutputFormatter."""

    def test_init(self):
        """Test initialization."""
        formatter = OutputFormatter(max_raw_display=300)
        assert formatter.max_raw_display == 300

    def test_init_default(self):
        """Test initialization with default value."""
        formatter = OutputFormatter()
        assert formatter.max_raw_display == 500

    def test_format_summary_with_summary(self):
        """Test formatting output with summary."""
        formatter = OutputFormatter()
        chunk = OutputChunk(
            instance_name="test-instance",
            raw_output="Short output",
            summary="This is a summary",
            is_complete=True,
        )

        result = formatter.format_summary(chunk)

        assert "[test-instance]" in result
        assert "✓" in result  # Completion indicator
        assert "📝 Summary: This is a summary" in result
        assert "Short output" in result
        assert "```" in result

    def test_format_summary_incomplete(self):
        """Test formatting incomplete output."""
        formatter = OutputFormatter()
        chunk = OutputChunk(
            instance_name="test-instance",
            raw_output="Incomplete",
            summary="Summary",
            is_complete=False,
        )

        result = formatter.format_summary(chunk)

        assert "[test-instance]" in result
        assert "⋯" in result  # Incomplete indicator
        assert "Summary" in result

    def test_format_summary_long_output_truncated(self):
        """Test formatting with long output truncated."""
        formatter = OutputFormatter(max_raw_display=100)
        long_output = "x" * 500
        chunk = OutputChunk(
            instance_name="test",
            raw_output=long_output,
            summary="Summary of long output",
            is_complete=True,
        )

        result = formatter.format_summary(chunk)

        assert "Summary of long output" in result
        assert "(truncated, 500 chars total)" in result
        # Should show only first 100 chars
        assert long_output[:100] in result
        assert len(result) < len(long_output)

    def test_format_summary_no_summary(self):
        """Test formatting without summary shows raw output."""
        formatter = OutputFormatter()
        chunk = OutputChunk(
            instance_name="test", raw_output="Raw output only", is_complete=True
        )

        result = formatter.format_summary(chunk)

        assert "[test]" in result
        assert "Raw output only" in result
        # Should not have summary section
        assert "📝 Summary:" not in result

    def test_format_raw_short_output(self):
        """Test formatting raw output."""
        formatter = OutputFormatter()
        chunk = OutputChunk(
            instance_name="test", raw_output="Short raw output", is_complete=True
        )

        result = formatter.format_raw(chunk)

        assert "[test]" in result
        assert "✓" in result
        assert "Short raw output" in result
        assert "```" in result

    def test_format_raw_long_output_truncated(self):
        """Test formatting raw output with truncation."""
        formatter = OutputFormatter(max_raw_display=50)
        long_output = "x" * 200
        chunk = OutputChunk(
            instance_name="test", raw_output=long_output, is_complete=False
        )

        result = formatter.format_raw(chunk, truncate=True)

        assert "[test]" in result
        assert "⋯" in result
        assert long_output[:50] in result
        assert "(truncated)" in result

    def test_format_raw_no_truncation(self):
        """Test formatting raw output without truncation."""
        formatter = OutputFormatter(max_raw_display=50)
        long_output = "x" * 200
        chunk = OutputChunk(instance_name="test", raw_output=long_output)

        result = formatter.format_raw(chunk, truncate=False)

        assert long_output in result
        assert "(truncated)" not in result

    def test_format_status(self):
        """Test formatting status message."""
        formatter = OutputFormatter()
        result = formatter.format_status("instance1", "Processing...")

        assert "[instance1]" in result
        assert "ℹ️" in result
        assert "Processing..." in result

    def test_format_error(self):
        """Test formatting error message."""
        formatter = OutputFormatter()
        result = formatter.format_error("instance1", "Connection failed")

        assert "[instance1]" in result
        assert "❌" in result
        assert "Error: Connection failed" in result

    def test_format_preserves_instance_name(self):
        """Test that all formats preserve instance name."""
        formatter = OutputFormatter()
        instance_name = "my-special-instance-123"
        chunk = OutputChunk(instance_name=instance_name, raw_output="test")

        summary_result = formatter.format_summary(chunk)
        raw_result = formatter.format_raw(chunk)
        status_result = formatter.format_status(instance_name, "status")
        error_result = formatter.format_error(instance_name, "error")

        assert instance_name in summary_result
        assert instance_name in raw_result
        assert instance_name in status_result
        assert instance_name in error_result

    def test_format_handles_empty_output(self):
        """Test formatting handles empty output."""
        formatter = OutputFormatter()
        chunk = OutputChunk(instance_name="test", raw_output="", is_complete=True)

        result = formatter.format_raw(chunk)

        assert "[test]" in result
        assert "```" in result
        # Should not crash on empty output

    def test_format_handles_multiline_output(self):
        """Test formatting handles multiline output."""
        formatter = OutputFormatter()
        multiline = "Line 1\nLine 2\nLine 3"
        chunk = OutputChunk(instance_name="test", raw_output=multiline)

        result = formatter.format_raw(chunk)

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
