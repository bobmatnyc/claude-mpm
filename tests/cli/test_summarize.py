"""
Tests for document summarization command.

Test Coverage:
- Basic summarization with all styles
- Word limit enforcement
- Line limit functionality
- Output format variations
- Error handling (missing files, invalid UTF-8)
- Edge cases (empty files, single paragraph, code blocks)
"""

import json
import tempfile
from pathlib import Path

import pytest

from claude_mpm.cli.commands.summarize import (
    DocumentSummarizer,
    OutputFormat,
    SummaryStyle,
    format_output,
    summarize_command,
)

# Test data
SAMPLE_CONTENT = """
Introduction to Python Programming

Python is a high-level, interpreted programming language known for its simplicity and readability. It was created by Guido van Rossum and first released in 1991. Python emphasizes code readability with its notable use of significant whitespace.

Key Features and Benefits

Python supports multiple programming paradigms including procedural, object-oriented, and functional programming. However, one of the most important aspects is its extensive standard library. The language's design philosophy emphasizes code readability and simplicity.

Applications in Modern Development

Python is widely used in web development, data science, machine learning, and automation. Therefore, many companies have adopted Python as their primary language. It is critical to note that Python's ecosystem includes powerful frameworks like Django and Flask.

Community and Ecosystem

The Python community is large and supportive, providing extensive documentation and resources. Python has become one of the most popular programming languages in the world. Its package index, PyPI, contains hundreds of thousands of projects.

Conclusion and Future

Python continues to evolve with new features and improvements. The language remains relevant and widely adopted across various industries. Its simplicity and power make it an excellent choice for both beginners and experienced developers.
"""

CODE_SAMPLE = """
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total

# Example usage
result = calculate_sum([1, 2, 3, 4, 5])
print(f"Sum: {result}")
"""


class TestDocumentSummarizer:
    """Test DocumentSummarizer class."""

    def test_brief_summary(self):
        """Test brief summary extracts first paragraph."""
        summarizer = DocumentSummarizer(max_words=200)
        summary = summarizer.summarize(SAMPLE_CONTENT, SummaryStyle.BRIEF)

        assert "Python is a high-level" in summary
        assert "readability" in summary
        assert len(summary.split()) <= 200

    def test_detailed_summary(self):
        """Test detailed summary includes key sentences."""
        summarizer = DocumentSummarizer(max_words=300)
        summary = summarizer.summarize(SAMPLE_CONTENT, SummaryStyle.DETAILED)

        # Should contain opening
        assert "Python is a high-level" in summary

        # Should contain middle content with key markers
        assert any(
            marker in summary.lower()
            for marker in ["however", "therefore", "important", "critical"]
        )

        # Should contain conclusion
        assert "Python continues to evolve" in summary

    def test_bullet_points_summary(self):
        """Test bullet points format."""
        summarizer = DocumentSummarizer(max_words=250)
        summary = summarizer.summarize(SAMPLE_CONTENT, SummaryStyle.BULLET_POINTS)

        # Should be markdown bullets
        lines = summary.split("\n")
        assert all(line.startswith("-") for line in lines if line.strip())

        # Should have multiple points
        assert len(lines) >= 2

    def test_executive_summary(self):
        """Test executive summary includes opening and closing."""
        summarizer = DocumentSummarizer(max_words=200)
        summary = summarizer.summarize(SAMPLE_CONTENT, SummaryStyle.EXECUTIVE)

        # Should contain opening paragraph
        assert "Python is a high-level" in summary

        # Should contain closing paragraph
        assert "Python continues to evolve" in summary

        # Should NOT contain middle content
        assert "Python community" not in summary

    def test_word_limit_enforcement(self):
        """Test word limit truncation."""
        summarizer = DocumentSummarizer(max_words=50)
        summary = summarizer.summarize(SAMPLE_CONTENT, SummaryStyle.DETAILED)

        word_count = len(summary.split())
        assert word_count <= 51  # Allow for ellipsis word

        # Should have ellipsis if truncated
        if word_count > 50:
            assert summary.endswith("...")

    def test_line_limit(self):
        """Test line limit functionality."""
        summarizer = DocumentSummarizer(max_words=200)
        content_lines = SAMPLE_CONTENT.split("\n")
        line_limit = 5

        summary = summarizer.summarize(
            SAMPLE_CONTENT, SummaryStyle.BRIEF, lines_limit=line_limit
        )

        # Should only process first N lines
        # Content should not include paragraphs beyond line limit
        assert "Python continues to evolve" not in summary

    def test_single_paragraph(self):
        """Test handling of single paragraph content."""
        content = "This is a single paragraph document. It has only one paragraph."
        summarizer = DocumentSummarizer(max_words=100)

        # Brief should return the paragraph
        brief = summarizer.summarize(content, SummaryStyle.BRIEF)
        assert "single paragraph" in brief

        # Executive should return same (only one paragraph)
        executive = summarizer.summarize(content, SummaryStyle.EXECUTIVE)
        assert brief == executive

    def test_empty_content(self):
        """Test handling of empty content."""
        summarizer = DocumentSummarizer(max_words=100)
        summary = summarizer.summarize("", SummaryStyle.BRIEF)
        assert summary == ""

    def test_code_block_filtering(self):
        """Test that code blocks are filtered out."""
        # Content with mixed prose and code blocks
        mixed_content = """
This is a document about Python functions and how they work in practice.

    def calculate_sum(numbers):
        total = 0
        for num in numbers:
            total += num
        return total

The above function demonstrates a simple iterative approach to summing numbers.

    # Example usage
    result = calculate_sum([1, 2, 3, 4, 5])

In conclusion, functions are reusable blocks of code that perform specific tasks.
        """
        summarizer = DocumentSummarizer(max_words=100)
        summary = summarizer.summarize(mixed_content, SummaryStyle.BRIEF)

        # Should extract prose, not code blocks
        assert "document about Python" in summary
        # Code with def should be filtered
        assert "def calculate_sum" not in summary

    def test_paragraph_extraction(self):
        """Test paragraph extraction filters correctly."""
        summarizer = DocumentSummarizer(max_words=200)
        paragraphs = summarizer._extract_paragraphs(SAMPLE_CONTENT)

        # Should have multiple paragraphs
        assert len(paragraphs) >= 4

        # Should not include very short paragraphs (headers)
        for para in paragraphs:
            assert len(para) >= 40

        # Should not include empty lines
        for para in paragraphs:
            assert para.strip()

    def test_sentence_splitting(self):
        """Test sentence splitting handles abbreviations."""
        summarizer = DocumentSummarizer(max_words=200)
        text = "Dr. Smith works at MIT. He studies e.g. machine learning and i.e. AI."
        sentences = summarizer._split_sentences(text)

        # Should have 2 sentences, not split on abbreviations
        assert len(sentences) == 2
        assert "Dr. Smith" in sentences[0]
        assert "e.g." in sentences[1]
        assert "i.e." in sentences[1]


class TestOutputFormatting:
    """Test output formatting functions."""

    def test_text_format(self):
        """Test plain text output."""
        summary = "This is a summary."
        file_path = Path("test.txt")

        output = format_output(summary, OutputFormat.TEXT, file_path)
        assert output == summary

    def test_json_format(self):
        """Test JSON output."""
        summary = "This is a summary."
        file_path = Path("test.txt")

        output = format_output(summary, OutputFormat.JSON, file_path)
        data = json.loads(output)

        assert data["file"] == "test.txt"
        assert data["summary"] == summary
        assert data["word_count"] == 4

    def test_markdown_format(self):
        """Test markdown output."""
        summary = "This is a summary."
        file_path = Path("test.txt")

        output = format_output(summary, OutputFormat.MARKDOWN, file_path)

        assert output.startswith("# Summary: test.txt")
        assert summary in output


class TestSummarizeCommand:
    """Test summarize_command function (integration tests)."""

    def test_summarize_existing_file(self, tmp_path):
        """Test summarizing an existing file."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text(SAMPLE_CONTENT, encoding="utf-8")

        # Mock args
        class Args:
            file_path = str(test_file)
            style = "brief"
            max_words = 100
            output = "text"
            lines = None

        result = summarize_command(Args())
        assert result == 0

    def test_summarize_missing_file(self):
        """Test error handling for missing file."""

        class Args:
            file_path = "/nonexistent/file.txt"
            style = "brief"
            max_words = 100
            output = "text"
            lines = None

        result = summarize_command(Args())
        assert result == 1

    def test_summarize_directory(self, tmp_path):
        """Test error handling for directory path."""

        class Args:
            file_path = str(tmp_path)
            style = "brief"
            max_words = 100
            output = "text"
            lines = None

        result = summarize_command(Args())
        assert result == 1

    def test_summarize_with_line_limit(self, tmp_path):
        """Test line limit functionality."""
        test_file = tmp_path / "test.txt"
        test_file.write_text(SAMPLE_CONTENT, encoding="utf-8")

        class Args:
            file_path = str(test_file)
            style = "brief"
            max_words = 150
            output = "text"
            lines = 5

        result = summarize_command(Args())
        assert result == 0

    def test_summarize_all_styles(self, tmp_path):
        """Test all summary styles."""
        test_file = tmp_path / "test.txt"
        test_file.write_text(SAMPLE_CONTENT, encoding="utf-8")

        styles = ["brief", "detailed", "bullet_points", "executive"]

        for summary_style in styles:

            class Args:
                file_path = str(test_file)
                style = summary_style
                max_words = 200
                output = "text"
                lines = None

            result = summarize_command(Args())
            assert result == 0, f"Failed for style: {summary_style}"

    def test_summarize_all_output_formats(self, tmp_path):
        """Test all output formats."""
        test_file = tmp_path / "test.txt"
        test_file.write_text(SAMPLE_CONTENT, encoding="utf-8")

        formats = ["text", "json", "markdown"]

        for fmt in formats:

            class Args:
                file_path = str(test_file)
                style = "brief"
                max_words = 100
                output = fmt
                lines = None

            result = summarize_command(Args())
            assert result == 0, f"Failed for format: {fmt}"

    def test_summarize_unicode_error(self, tmp_path):
        """Test error handling for non-UTF-8 files."""
        test_file = tmp_path / "test.bin"
        # Write binary data that's not valid UTF-8
        test_file.write_bytes(b"\x80\x81\x82\x83")

        class Args:
            file_path = str(test_file)
            style = "brief"
            max_words = 100
            output = "text"
            lines = None

        result = summarize_command(Args())
        assert result == 1


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_content(self):
        """Test handling of very long content."""
        # Generate large content
        long_content = "\n\n".join([f"Paragraph {i}. " * 50 for i in range(100)])
        summarizer = DocumentSummarizer(max_words=200)

        summary = summarizer.summarize(long_content, SummaryStyle.BRIEF)
        assert len(summary.split()) <= 201  # Allow for ellipsis

    def test_max_words_zero(self):
        """Test zero max_words (should return empty or minimal)."""
        summarizer = DocumentSummarizer(max_words=0)
        summary = summarizer.summarize(SAMPLE_CONTENT, SummaryStyle.BRIEF)

        # Should return ellipsis only
        assert summary == "..."

    def test_max_words_one(self):
        """Test max_words=1 edge case."""
        summarizer = DocumentSummarizer(max_words=1)
        summary = summarizer.summarize(SAMPLE_CONTENT, SummaryStyle.BRIEF)

        # Should return first word + ellipsis
        assert summary.startswith("Python") or summary.endswith("...")

    def test_whitespace_only_content(self):
        """Test content with only whitespace."""
        content = "   \n\n\t\t\n   "
        summarizer = DocumentSummarizer(max_words=100)

        summary = summarizer.summarize(content, SummaryStyle.BRIEF)
        assert summary == ""

    def test_single_sentence(self):
        """Test single sentence content."""
        content = "This is a single sentence."
        summarizer = DocumentSummarizer(max_words=100)

        for style in SummaryStyle:
            summary = summarizer.summarize(content, style)
            assert "single sentence" in summary

    def test_no_key_markers(self):
        """Test detailed summary without key markers."""
        content = """
First paragraph.

Middle paragraph.

Last paragraph.
        """
        summarizer = DocumentSummarizer(max_words=100)
        summary = summarizer.summarize(content, SummaryStyle.DETAILED)

        # Should still have first and last
        assert "First" in summary
        assert "Last" in summary


# Pytest fixtures for integration tests
@pytest.fixture
def sample_file(tmp_path):
    """Create sample file for testing."""
    test_file = tmp_path / "sample.txt"
    test_file.write_text(SAMPLE_CONTENT, encoding="utf-8")
    return test_file


def test_integration_brief_summary(sample_file):
    """Integration test: brief summary of sample file."""

    class Args:
        file_path = str(sample_file)
        style = "brief"
        max_words = 150
        output = "text"
        lines = None

    result = summarize_command(Args())
    assert result == 0


def test_integration_json_output(sample_file, capsys):
    """Integration test: JSON output format."""

    class Args:
        file_path = str(sample_file)
        style = "brief"
        max_words = 100
        output = "json"
        lines = None

    result = summarize_command(Args())
    assert result == 0

    # Verify JSON output
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "summary" in data
    assert "word_count" in data
    assert "file" in data
