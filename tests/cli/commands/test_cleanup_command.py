"""
Comprehensive tests for the CleanupCommand class.

WHY: The cleanup command manages Claude conversation history cleanup to reduce
memory usage. This is important for preventing memory issues with large .claude.json files.

DESIGN DECISIONS:
- Test validate_args method with valid and invalid inputs
- Test run method with mocked file operations
- Test dry-run mode for safety
- Verify proper CommandResult handling
- Test error handling scenarios
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.cli.commands.cleanup import (
    CleanupCommand,
    analyze_claude_json,
    format_size,
    parse_size,
)
from claude_mpm.cli.shared.base_command import CommandResult


class TestParseSizeFunction:
    """Test the parse_size helper function."""

    def test_parse_bytes(self):
        """Test parsing byte values."""
        assert parse_size("100B") == 100
        assert parse_size("100b") == 100

    def test_parse_kilobytes(self):
        """Test parsing kilobyte values."""
        assert parse_size("1KB") == 1024
        assert parse_size("500KB") == 500 * 1024

    def test_parse_megabytes(self):
        """Test parsing megabyte values."""
        assert parse_size("1MB") == 1024 * 1024
        assert parse_size("10MB") == 10 * 1024 * 1024

    def test_parse_gigabytes(self):
        """Test parsing gigabyte values."""
        assert parse_size("1GB") == 1024 * 1024 * 1024

    def test_parse_raw_number(self):
        """Test parsing raw number as bytes."""
        assert parse_size("1024") == 1024

    def test_parse_invalid_format(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            parse_size("invalid")


class TestFormatSizeFunction:
    """Test the format_size helper function."""

    def test_format_bytes(self):
        """Test formatting byte values."""
        assert format_size(100) == "100.0B"

    def test_format_kilobytes(self):
        """Test formatting kilobyte values."""
        result = format_size(1024)
        assert "KB" in result

    def test_format_megabytes(self):
        """Test formatting megabyte values."""
        result = format_size(1024 * 1024)
        assert "MB" in result

    def test_format_gigabytes(self):
        """Test formatting gigabyte values."""
        result = format_size(1024 * 1024 * 1024)
        assert "GB" in result


class TestCleanupCommand:
    """Test CleanupCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = CleanupCommand()

    def test_validate_args_default(self):
        """Test validation with default args."""
        args = Namespace(max_size="500KB", days=30)
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_valid_max_size(self):
        """Test validation with various valid max_size values."""
        valid_sizes = ["100KB", "1MB", "500KB", "2GB"]

        for size in valid_sizes:
            args = Namespace(max_size=size, days=30)
            error = self.command.validate_args(args)
            assert error is None, f"Size {size} should be valid"

    def test_validate_args_invalid_max_size(self):
        """Test validation with invalid max_size."""
        args = Namespace(max_size="invalid_size", days=30)
        error = self.command.validate_args(args)
        assert error is not None
        assert "Invalid size format" in error

    def test_validate_args_negative_days(self):
        """Test validation with negative days value."""
        args = Namespace(max_size="500KB", days=-1)
        error = self.command.validate_args(args)
        assert error is not None
        assert "positive" in error.lower()

    def test_validate_args_missing_max_size_uses_default(self):
        """Test validation when max_size is missing uses default."""
        args = Namespace(days=30)
        error = self.command.validate_args(args)
        assert error is None

    def test_run_no_claude_json_file(self, tmp_path):
        """Test run when .claude.json doesn't exist."""
        # Use a temp directory as fake home
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        with patch("claude_mpm.cli.commands.cleanup.Path.home", return_value=fake_home):
            # Use dry_run=True since there's no file to actually clean
            args = Namespace(
                max_size="500KB",
                days=30,
                archive=True,
                force=True,
                dry_run=True,
                format="json",
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            assert result.data is not None
            assert result.data.get("file_exists") is False

    def test_run_dry_run_mode(self, tmp_path):
        """Test run in dry-run mode."""
        # Create a fake .claude.json file
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        claude_json = fake_home / ".claude.json"
        claude_json.write_text('{"test": "data"}')

        with patch("claude_mpm.cli.commands.cleanup.Path.home", return_value=fake_home):
            args = Namespace(
                max_size="500KB",
                days=30,
                archive=True,
                force=True,
                dry_run=True,
                format="json",
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            assert "dry run" in result.message.lower()

    @patch("claude_mpm.cli.commands.cleanup.cleanup_memory")
    def test_run_text_format(self, mock_cleanup, tmp_path):
        """Test run with text format delegates to cleanup_memory."""
        # Create a fake .claude.json file
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        claude_json = fake_home / ".claude.json"
        claude_json.write_text('{"test": "data"}')

        with patch("claude_mpm.cli.commands.cleanup.Path.home", return_value=fake_home):
            args = Namespace(
                max_size="500KB",
                days=30,
                archive=True,
                force=True,
                dry_run=False,
                format="text",
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_cleanup.assert_called_once_with(args)

    def test_run_with_exception(self):
        """Test that exceptions are handled gracefully."""
        args = Namespace(
            max_size="500KB",
            days=30,
            archive=True,
            force=True,
            dry_run=False,
            format="json",
        )

        with patch.object(
            self.command,
            "_analyze_cleanup_needs",
            side_effect=Exception("Test error"),
        ):
            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is False
            assert "error" in result.message.lower()

    def test_analyze_cleanup_needs_file_exists(self, tmp_path):
        """Test _analyze_cleanup_needs when file exists."""
        # Create a large fake .claude.json file (larger than 500KB)
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        claude_json = fake_home / ".claude.json"
        # Create content larger than 500KB
        large_content = '{"data": "' + "x" * (600 * 1024) + '"}'
        claude_json.write_text(large_content)

        with patch("claude_mpm.cli.commands.cleanup.Path.home", return_value=fake_home):
            args = Namespace(
                max_size="500KB", days=30, archive=True, force=False, dry_run=False
            )

            result = self.command._analyze_cleanup_needs(args)

            assert result["file_exists"] is True
            assert result["needs_cleanup"] is True  # File > 500KB

    def test_analyze_cleanup_needs_file_not_exists(self, tmp_path):
        """Test _analyze_cleanup_needs when file doesn't exist."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        # Don't create .claude.json

        with patch("claude_mpm.cli.commands.cleanup.Path.home", return_value=fake_home):
            args = Namespace(max_size="500KB", days=30)

            result = self.command._analyze_cleanup_needs(args)

            assert result["file_exists"] is False
            assert result["needs_cleanup"] is False


class TestAnalyzeClaudeJson:
    """Test the analyze_claude_json helper function."""

    def test_analyze_nonexistent_file(self, tmp_path):
        """Test analyzing a file that doesn't exist."""
        nonexistent = tmp_path / "nonexistent.json"
        stats, issues = analyze_claude_json(nonexistent)

        assert stats["file_size"] == 0
        assert len(issues) > 0
        assert "not found" in issues[0].lower()

    def test_analyze_empty_json(self, tmp_path):
        """Test analyzing an empty JSON file."""
        json_file = tmp_path / ".claude.json"
        json_file.write_text("{}")

        stats, _issues = analyze_claude_json(json_file)

        assert stats["file_size"] > 0
        assert stats["line_count"] == 1
        assert stats["conversation_count"] == 0

    def test_analyze_valid_json(self, tmp_path):
        """Test analyzing a valid JSON file with conversations."""
        import json

        json_file = tmp_path / ".claude.json"
        data = {
            "conversation1": {"messages": [{"role": "user", "content": "Hello"}]},
            "conversation2": {"messages": [{"role": "user", "content": "Hi"}]},
        }
        json_file.write_text(json.dumps(data))

        stats, issues = analyze_claude_json(json_file)

        assert stats["file_size"] > 0
        assert stats["conversation_count"] == 2
        assert len(issues) == 0

    def test_analyze_invalid_json(self, tmp_path):
        """Test analyzing an invalid JSON file."""
        json_file = tmp_path / ".claude.json"
        json_file.write_text("{ invalid json }")

        _stats, issues = analyze_claude_json(json_file)

        assert len(issues) > 0
        assert "json" in issues[0].lower()
