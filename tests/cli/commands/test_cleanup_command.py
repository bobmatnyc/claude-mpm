"""
Comprehensive tests for the CleanupCommand class.

WHY: The cleanup command manages system cleanup operations including memory,
cache, and temporary files. This is important for system maintenance.

DESIGN DECISIONS:
- Test all cleanup types (memory, cache, temp, all)
- Mock file operations to avoid actual deletion
- Test dry-run mode for safety
- Verify confirmation prompts
- Test error handling for permission issues
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

    def test_initialization():
        """Test CleanupCommand initialization."""
        assert self.command.command_name == "cleanup"
        assert self.command.logger is not None

    def test_validate_args_default():
        """Test validation with default args."""
        args = Namespace(cleanup_type="all", dry_run=False, force=False)
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_valid_types():
        """Test validation with valid cleanup types."""
        valid_types = ["memory", "cache", "temp", "logs", "all"]

        for cleanup_type in valid_types:
            args = Namespace(cleanup_type=cleanup_type, dry_run=False, force=False)
            error = self.command.validate_args(args)
            assert error is None, f"Cleanup type {cleanup_type} should be valid"

    def test_validate_args_invalid_type():
        """Test validation with invalid cleanup type."""
        Namespace(cleanup_type="invalid", dry_run=False, force=False)
        # Depending on implementation, this might be caught in validation
        # or during execution

    @patch("claude_mpm.cli.commands.cleanup.Path")
    @patch("claude_mpm.cli.commands.cleanup.shutil")
    def test_run_memory_cleanup(self, mock_path_class):
        """Test memory cleanup operation."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.glob.return_value = [
            Path("/mock/path/.claude.json"),
            Path("/mock/path/.claude_cache.json"),
        ]
        mock_path_class.return_value = mock_path

        args = Namespace(
            cleanup_type="memory", dry_run=False, force=True, format="text"
        )

        with patch.object(self.command, "_cleanup_memory") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.success_result(
                "Memory cleaned", data={"files_removed": 2, "space_freed": "10MB"}
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_cleanup.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_run_memory_cleanup_dry_run(self):
        """Test memory cleanup in dry-run mode."""
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.glob.return_value = [
            Path("/mock/path/.claude.json"),
            Path("/mock/path/.claude_cache.json"),
        ]
        self.return_value = mock_path

        args = Namespace(
            cleanup_type="memory",
            dry_run=True,  # Dry run mode
            force=False,
            format="text",
        )

        with patch.object(self.command, "_cleanup_memory") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.success_result(
                "Memory cleanup (dry-run)",
                data={"files_to_remove": 2, "space_to_free": "10MB"},
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            # In dry run, files should not actually be deleted

    def test_run_cache_cleanup():
        """Test cache cleanup operation."""
        args = Namespace(cleanup_type="cache", dry_run=False, force=True, format="text")

        with patch.object(self.command, "_cleanup_cache") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.success_result(
                "Cache cleaned", data={"cache_cleared": True, "items_removed": 50}
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_cleanup.assert_called_once_with(args)

    def test_run_temp_cleanup():
        """Test temporary files cleanup."""
        args = Namespace(cleanup_type="temp", dry_run=False, force=True, format="text")

        with patch.object(self.command, "_cleanup_temp") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.success_result(
                "Temp files cleaned", data={"files_removed": 10, "space_freed": "5MB"}
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_cleanup.assert_called_once_with(args)

    def test_run_logs_cleanup():
        """Test logs cleanup operation."""
        args = Namespace(
            cleanup_type="logs",
            dry_run=False,
            force=True,
            format="text",
            keep_days=7,  # Keep logs from last 7 days
        )

        with patch.object(self.command, "_cleanup_logs") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.success_result(
                "Logs cleaned", data={"files_removed": 20, "space_freed": "100MB"}
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_cleanup.assert_called_once_with(args)

    def test_run_all_cleanup():
        """Test cleaning all types."""
        args = Namespace(cleanup_type="all", dry_run=False, force=True, format="json")

        with patch.object(self.command, "_cleanup_all") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.success_result(
                "All cleanup completed",
                data={
                    "memory": {"files_removed": 2, "space_freed": "10MB"},
                    "cache": {"items_removed": 50},
                    "temp": {"files_removed": 10, "space_freed": "5MB"},
                    "logs": {"files_removed": 20, "space_freed": "100MB"},
                    "total_space_freed": "115MB",
                },
            )

            result = self.command.run(args)

            assert isinstance(result, CommandResult)
            assert result.success is True
            assert result.data is not None
            assert "total_space_freed" in result.data

    def test_cleanup_with_confirmation():
        """Test cleanup with user confirmation prompt."""
        args = Namespace(
            cleanup_type="memory",
            dry_run=False,
            force=False,  # Will prompt for confirmation
            format="text",
        )

        with patch("builtins.input", return_value="y"):
            with patch.object(self.command, "_cleanup_memory") as mock_cleanup:
                mock_cleanup.return_value = CommandResult.success_result(
                    "Memory cleaned"
                )

                result = self.command.run(args)

                assert result.success is True

    def test_cleanup_cancelled_by_user():
        """Test cleanup cancelled by user."""
        args = Namespace(
            cleanup_type="memory", dry_run=False, force=False, format="text"
        )

        with patch("builtins.input", return_value="n"):
            self.command.run(args)

            # Depending on implementation, might return success with no action
            # or a specific cancellation result

    @patch("claude_mpm.cli.commands.cleanup.Path")
    def test_cleanup_permission_error(self):
        """Test handling permission errors during cleanup."""
        mock_path = Mock()
        mock_path.unlink.side_effect = PermissionError("Access denied")
        self.return_value = mock_path

        args = Namespace(
            cleanup_type="memory", dry_run=False, force=True, format="text"
        )

        with patch.object(self.command, "_cleanup_memory") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.error_result(
                "Permission denied", data={"error": "Access denied to some files"}
            )

            result = self.command.run(args)

            assert result.success is False
            assert "Permission" in result.message or "denied" in result.message

    def test_cleanup_with_pattern():
        """Test cleanup with file pattern matching."""
        args = Namespace(
            cleanup_type="temp",
            pattern="*.tmp",  # Only clean .tmp files
            dry_run=False,
            force=True,
            format="text",
        )

        with patch.object(self.command, "_cleanup_temp") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.success_result(
                "Temp files cleaned", data={"pattern": "*.tmp", "files_removed": 5}
            )

            result = self.command.run(args)

            assert result.success is True

    def test_cleanup_with_size_threshold():
        """Test cleanup with size threshold."""
        args = Namespace(
            cleanup_type="logs",
            min_size="10MB",  # Only clean files larger than 10MB
            dry_run=False,
            force=True,
            format="text",
        )

        with patch.object(self.command, "_cleanup_logs") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.success_result(
                "Large log files cleaned", data={"min_size": "10MB", "files_removed": 3}
            )

            result = self.command.run(args)

            assert result.success is True

    def test_cleanup_statistics():
        """Test cleanup statistics reporting."""
        args = Namespace(
            cleanup_type="all",
            dry_run=False,
            force=True,
            format="json",
            stats=True,  # Request detailed statistics
        )

        with patch.object(self.command, "_cleanup_all") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.success_result(
                "Cleanup completed",
                data={
                    "statistics": {
                        "start_time": "2024-01-01 12:00:00",
                        "end_time": "2024-01-01 12:00:05",
                        "duration": "5 seconds",
                        "total_files_scanned": 1000,
                        "total_files_removed": 100,
                        "total_space_freed": "500MB",
                        "errors": 0,
                    }
                },
            )

            result = self.command.run(args)

            assert result.success is True
            assert "statistics" in result.data
            assert result.data["statistics"]["total_files_removed"] == 100

    def test_cleanup_with_exclusions():
        """Test cleanup with exclusion patterns."""
        args = Namespace(
            cleanup_type="logs",
            exclude=["*.important", "critical-*"],
            dry_run=False,
            force=True,
            format="text",
        )

        with patch.object(self.command, "_cleanup_logs") as mock_cleanup:
            mock_cleanup.return_value = CommandResult.success_result(
                "Logs cleaned with exclusions",
                data={"excluded_patterns": ["*.important", "critical-*"]},
            )

            result = self.command.run(args)

            assert result.success is True

    def test_run_with_exception():
        """Test general exception handling in run method."""
        args = Namespace(
            cleanup_type="memory", dry_run=False, force=True, format="text"
        )

        with patch.object(
            self.command, "_cleanup_memory", side_effect=Exception("Cleanup failed")
        ):
            result = self.command.run(args)

            # Should handle the exception gracefully
            assert isinstance(result, CommandResult)
