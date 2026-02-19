#!/usr/bin/env python3
"""
Tests for AgentOutputFormatter
===============================

Tests for table formatting and agent output formatting functionality.
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from claude_mpm.services.cli.agent_output_formatter import AgentOutputFormatter


class TestAgentOutputFormatter:
    """Test suite for AgentOutputFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return AgentOutputFormatter()

    def test_format_as_table_validates_column_count(self, formatter):
        """Verify table formatting handles uneven rows correctly."""
        headers = ["Name", "Version", "Description"]
        rows = [
            ["agent1", "1.0.0", "First agent"],
            ["agent2", "2.0.0"],  # Missing description
            ["agent3"],  # Missing version and description
        ]

        result = formatter.format_as_table(headers, rows, min_column_width=10)
        lines = result.split("\n")

        # Verify all rows have consistent column structure
        header_line = lines[0]
        separator_line = lines[1]

        # Each data row should have same number of separators as header
        expected_separators = header_line.count("|")

        for i, line in enumerate(lines[2:], start=2):
            if line.strip():
                actual_separators = line.count("|")
                assert actual_separators == expected_separators, (
                    f"Row {i} has {actual_separators} separators, expected {expected_separators}"
                )

    def test_format_as_table_with_equal_rows(self, formatter):
        """Test table formatting with equal-length rows."""
        headers = ["Name", "Version"]
        rows = [["agent1", "1.0.0"], ["agent2", "2.0.0"], ["agent3", "3.0.0"]]

        result = formatter.format_as_table(headers, rows)

        lines = result.split("\n")
        assert len(lines) == 5  # Header + separator + 3 data rows

        # All lines should have same number of separators
        separator_count = lines[0].count("|")
        for line in lines[2:]:  # Skip separator line
            assert line.count("|") == separator_count

    def test_format_as_table_with_empty_rows(self, formatter):
        """Test table formatting with completely empty rows."""
        headers = ["Name", "Version", "Description"]
        rows = [
            ["agent1", "1.0.0", "First"],
            [],  # Completely empty row
            ["agent3", "3.0.0", "Third"],
        ]

        result = formatter.format_as_table(headers, rows)
        lines = result.split("\n")

        # Should still have consistent column structure
        header_line = lines[0]
        expected_separators = header_line.count("|")

        for i, line in enumerate(lines[2:], start=2):
            if line.strip():
                actual_separators = line.count("|")
                assert actual_separators == expected_separators, (
                    f"Row {i} has {actual_separators} separators, expected {expected_separators}"
                )

    def test_format_as_table_handles_none_values(self, formatter):
        """Test table formatting with None values in cells."""
        headers = ["Name", "Version"]
        rows = [["agent1", None], [None, "2.0.0"], ["agent3", "3.0.0"]]

        result = formatter.format_as_table(headers, rows)

        # Should not crash and should format None as string
        assert (
            "None" in result or "    " in result
        )  # None converted to string or padded space

    def test_format_as_table_proper_padding(self, formatter):
        """Test that cells are properly padded to column widths."""
        headers = ["Short", "VeryLongHeader"]
        rows = [["A", "B"], ["CD", "EF"]]

        result = formatter.format_as_table(headers, rows, min_column_width=5)
        lines = result.split("\n")

        # Header line should have proper padding
        header_line = lines[0]
        # "VeryLongHeader" should determine the second column width
        assert len(header_line) > 20  # At least "Short | VeryLongHeader"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
