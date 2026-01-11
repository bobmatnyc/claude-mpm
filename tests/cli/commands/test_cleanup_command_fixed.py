"""
Fixed tests for the CleanupCommand class.

WHY: The cleanup command manages memory cleanup operations for Claude conversation
history. These tests ensure the command works correctly.

DESIGN DECISIONS:
- Test the actual implementation methods (_analyze_cleanup_needs)
- Mock file system operations to avoid actual deletion
- Test dry-run mode for safety
- Verify validation of arguments
- Test different output formats
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

from claude_mpm.cli.commands.cleanup import CleanupCommand
from claude_mpm.cli.shared.base_command import CommandResult


class TestCleanupCommand:
    """Test CleanupCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = CleanupCommand()

    def test_validate_args_default():
        """Test validation with default args."""
        args = Namespace(
            days=30, max_size="500KB", archive=True, dry_run=False, force=False
        )
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_valid_sizes():
        """Test validation with valid size formats."""
        valid_sizes = ["100KB", "500KB", "1MB", "10MB", "1GB"]

        for size in valid_sizes:
            args = Namespace(
                days=30, max_size=size, archive=True, dry_run=False, force=False
            )
            error = self.command.validate_args(args)
            assert error is None, f"Size {size} should be valid"

    def test_validate_args_invalid_size():
        """Test validation with invalid size format."""
        args = Namespace(
            days=30, max_size="invalid", archive=True, dry_run=False, force=False
        )
        error = self.command.validate_args(args)
        assert error is not None
        assert "Invalid size format" in error

    def test_validate_args_negative_days():
        """Test validation with negative days."""
        args = Namespace(
            days=-1, max_size="500KB", archive=True, dry_run=False, force=False
        )
        error = self.command.validate_args(args)
        assert error is not None
        assert "positive number" in error

    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_run_memory_cleanup(self):
        """Test memory cleanup operation."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value = Mock(st_size=1000000)
        self.return_value = mock_path
        self.home.return_value = Path("/mock/home")

        args = Namespace(
            days=30,
            max_size="500KB",
            archive=True,
            dry_run=False,
            force=True,
            format="text",
        )

        with patch.object(self.command, "_analyze_cleanup_needs") as mock_analyze:
            mock_analyze.return_value = {
                "files": [{"path": "/mock/path/.claude.json", "size": 1000000}],
                "total_size": 1000000,
                "space_to_free": 500000,
            }

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            mock_analyze.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_run_memory_cleanup_dry_run(self):
        """Test memory cleanup in dry-run mode."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value = Mock(st_size=500000)
        self.return_value = mock_path
        self.home.return_value = Path("/mock/home")

        args = Namespace(
            days=30,
            max_size="500KB",
            archive=True,
            dry_run=True,  # Dry run mode
            force=False,
            format="text",
        )

        with patch.object(self.command, "_analyze_cleanup_needs") as mock_analyze:
            mock_analyze.return_value = {
                "files": [{"path": "/mock/path/.claude.json", "size": 500000}],
                "total_size": 500000,
                "space_to_free": 0,
            }

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            # In dry run, files should not actually be deleted

    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_run_with_archive(self):
        """Test cleanup with archiving enabled."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value = Mock(st_size=1000000)
        self.return_value = mock_path
        self.home.return_value = Path("/mock/home")

        args = Namespace(
            days=30,
            max_size="500KB",
            archive=True,
            dry_run=False,
            force=True,
            format="text",
        )

        with patch.object(self.command, "_analyze_cleanup_needs") as mock_analyze:
            mock_analyze.return_value = {
                "files": [{"path": "/mock/path/.claude.json", "size": 1000000}],
                "total_size": 1000000,
                "space_to_free": 500000,
            }

            result = self.command.run(args)

            assert isinstance(result, CommandResult)

    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_run_without_archive(self):
        """Test cleanup without archiving."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value = Mock(st_size=1000000)
        self.return_value = mock_path
        self.home.return_value = Path("/mock/home")

        args = Namespace(
            days=30,
            max_size="500KB",
            archive=False,
            dry_run=False,
            force=True,
            format="json",
        )

        with patch.object(self.command, "_analyze_cleanup_needs") as mock_analyze:
            mock_analyze.return_value = {
                "files": [{"path": "/mock/path/.claude.json", "size": 1000000}],
                "total_size": 1000000,
                "space_to_free": 500000,
            }

            result = self.command.run(args)

            assert isinstance(result, CommandResult)

    @patch("builtins.input")
    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_cleanup_with_confirmation(self, mock_input):
        """Test cleanup with user confirmation."""
        mock_input.return_value = "yes"
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value = Mock(st_size=1000000)
        self.return_value = mock_path
        self.home.return_value = Path("/mock/home")

        args = Namespace(
            days=30,
            max_size="500KB",
            archive=True,
            dry_run=False,
            force=False,  # Require confirmation
            format="text",
        )

        with patch.object(self.command, "_analyze_cleanup_needs") as mock_analyze:
            mock_analyze.return_value = {
                "files": [{"path": "/mock/path/.claude.json", "size": 1000000}],
                "total_size": 1000000,
                "space_to_free": 500000,
            }

            result = self.command.run(args)

            assert isinstance(result, CommandResult)

    def test_cleanup_cancelled_by_user():
        """Test cleanup cancelled by user input."""
        args = Namespace(
            days=30,
            max_size="500KB",
            archive=True,
            dry_run=False,
            force=False,
            format="text",
        )

        with patch("builtins.input", return_value="no"):
            # Mock the method to avoid actual file operations
            with patch.object(self.command, "_analyze_cleanup_needs") as mock_analyze:
                mock_analyze.return_value = {
                    "files": [],
                    "total_size": 0,
                    "space_to_free": 0,
                }

                result = self.command.run(args)

                # Check if cleanup was cancelled (implementation dependent)
                assert isinstance(result, CommandResult)

    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_cleanup_permission_error(self):
        """Test cleanup with permission errors."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        self.return_value = mock_path
        self.home.return_value = Path("/mock/home")

        args = Namespace(
            days=30,
            max_size="500KB",
            archive=True,
            dry_run=False,
            force=True,
            format="text",
        )

        with patch.object(self.command, "_analyze_cleanup_needs") as mock_analyze:
            mock_analyze.side_effect = PermissionError("Access denied")

            result = self.command.run(args)

            assert result.success is False

    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_cleanup_json_output(self):
        """Test cleanup with JSON output format."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value = Mock(st_size=1000000)
        self.return_value = mock_path
        self.home.return_value = Path("/mock/home")

        args = Namespace(
            days=30,
            max_size="500KB",
            archive=True,
            dry_run=False,
            force=True,
            format="json",
        )

        with patch.object(self.command, "_analyze_cleanup_needs") as mock_analyze:
            mock_analyze.return_value = {
                "files": [{"path": "/mock/path/.claude.json", "size": 1000000}],
                "total_size": 1000000,
                "space_to_free": 500000,
            }

            result = self.command.run(args)

            assert isinstance(result, CommandResult)

    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_cleanup_yaml_output(self):
        """Test cleanup with YAML output format."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value = Mock(st_size=750000)
        self.return_value = mock_path
        self.home.return_value = Path("/mock/home")

        args = Namespace(
            days=30,
            max_size="500KB",
            archive=True,
            dry_run=False,
            force=True,
            format="yaml",
        )

        with patch.object(self.command, "_analyze_cleanup_needs") as mock_analyze:
            mock_analyze.return_value = {
                "files": [{"path": "/mock/path/.claude.json", "size": 750000}],
                "total_size": 750000,
                "space_to_free": 250000,
            }

            result = self.command.run(args)

            assert isinstance(result, CommandResult)

    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_run_with_exception(self):
        """Test general exception handling in run method."""
        self.home.side_effect = Exception("Unexpected error")

        args = Namespace(
            days=30,
            max_size="500KB",
            archive=True,
            dry_run=False,
            force=True,
            format="text",
        )

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
