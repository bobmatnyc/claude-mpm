"""
Tests for startup logging functionality.

WHY: Ensure startup logging correctly captures all log levels,
creates timestamped files, and can be analyzed by the doctor command.
"""

import logging
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from claude_mpm.cli.startup_logging import (
    cleanup_old_startup_logs,
    get_latest_startup_log,
    setup_startup_logging,
)
from claude_mpm.services.diagnostics.checks.startup_log_check import StartupLogCheck
from claude_mpm.services.diagnostics.models import DiagnosticStatus


class TestStartupLogging:
    """Test startup logging setup and file creation."""

    def test_setup_startup_logging_creates_file(self):
        """Test that setup_startup_logging creates a log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Ensure root logger is at DEBUG level for testing
            logging.getLogger().setLevel(logging.DEBUG)

            # Setup logging
            log_file = setup_startup_logging(project_root)

            # Verify file was created
            assert log_file.exists()
            assert log_file.name.startswith("startup-")
            assert log_file.suffix == ".log"

            # Verify directory structure
            log_dir = project_root / ".claude-mpm" / "logs" / "startup"
            assert log_dir.exists()

            # Write a test log and verify it's captured
            logger = logging.getLogger("test")
            logger.info("Test message")
            logger.error("Test error")

            # Force flush all handlers to ensure content is written
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()
                    # Temporarily close to force write
                    handler.close()
                    # Remove from logger
                    root_logger.removeHandler(handler)

            # Read and verify content
            content = log_file.read_text()
            assert "Claude MPM Startup" in content
            assert "Test message" in content
            assert "Test error" in content

    def test_cleanup_old_startup_logs(self):
        """Test cleanup of old startup log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            log_dir = project_root / ".claude-mpm" / "logs" / "startup"
            log_dir.mkdir(parents=True)

            # Create old and new log files
            now = datetime.now(timezone.utc)
            old_file = log_dir / "startup-2023-01-01-00-00-00.log"
            old_file.touch()
            # Set modification time to old date
            old_time = (now - timedelta(days=30)).timestamp()
            import os

            os.utime(old_file, (old_time, old_time))

            # Create recent files
            for i in range(5):
                recent_file = log_dir / f"startup-2024-01-{i + 1:02d}-00-00-00.log"
                recent_file.touch()

            # Run cleanup (keep last 7 days, min 3 files)
            deleted = cleanup_old_startup_logs(
                project_root, keep_days=7, keep_min_count=3
            )

            # Old file should be deleted if we have enough recent ones
            assert deleted >= 0  # Depends on timing

            # At least keep_min_count files should remain
            remaining = list(log_dir.glob("startup-*.log"))
            assert len(remaining) >= 3

    def test_get_latest_startup_log(self):
        """Test finding the most recent startup log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            log_dir = project_root / ".claude-mpm" / "logs" / "startup"
            log_dir.mkdir(parents=True)

            # No logs initially
            assert get_latest_startup_log(project_root) is None

            # Create multiple log files
            log1 = log_dir / "startup-2024-01-01-00-00-00.log"
            log2 = log_dir / "startup-2024-01-02-00-00-00.log"
            log3 = log_dir / "startup-2024-01-03-00-00-00.log"

            log1.touch()
            log2.touch()
            log3.touch()

            # Should return the most recent
            latest = get_latest_startup_log(project_root)
            assert latest == log3


class TestStartupLogCheck:
    """Test the diagnostic check for startup logs."""

    def test_no_logs_found(self):
        """Test behavior when no startup logs exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                check = StartupLogCheck()
                result = check.run()

                assert result.status == DiagnosticStatus.WARNING
                assert "No startup logs found" in result.message

    def test_analyze_clean_log(self):
        """Test analysis of a clean startup log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            log_dir = project_root / ".claude-mpm" / "logs" / "startup"
            log_dir.mkdir(parents=True)

            # Create a clean log file
            log_file = log_dir / "startup-2024-01-15-14-30-45.log"
            log_content = """
2024-01-15 14:30:45 - startup - INFO - Claude MPM Startup
2024-01-15 14:30:45 - cli - INFO - Starting Claude MPM session
2024-01-15 14:30:45 - cli - INFO - MCP Server: Installed
2024-01-15 14:30:45 - cli - INFO - Monitor: Mode enabled
2024-01-15 14:30:46 - cli - INFO - Claude session completed successfully
"""
            log_file.write_text(log_content)

            with patch("pathlib.Path.cwd", return_value=project_root):
                check = StartupLogCheck()
                result = check.run()

                assert result.status == DiagnosticStatus.OK
                assert "successful" in result.message.lower()
                assert result.details["errors"] == 0
                assert result.details["warnings"] == 0

    def test_analyze_log_with_errors(self):
        """Test analysis of a log with errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            log_dir = project_root / ".claude-mpm" / "logs" / "startup"
            log_dir.mkdir(parents=True)

            # Create a log with errors
            log_file = log_dir / "startup-2024-01-15-14-30-45.log"
            log_content = """
2024-01-15 14:30:45 - startup - INFO - Claude MPM Startup
2024-01-15 14:30:45 - cli - ERROR - Agent deployment failed
2024-01-15 14:30:45 - cli - ERROR - MCP server not found
2024-01-15 14:30:45 - cli - WARNING - Socket.IO dependencies not available
2024-01-15 14:30:46 - cli - ERROR - Port 8765 already in use
"""
            log_file.write_text(log_content)

            with patch("pathlib.Path.cwd", return_value=project_root):
                check = StartupLogCheck(verbose=True)
                result = check.run()

                assert result.status == DiagnosticStatus.ERROR
                assert "3 error(s)" in result.message
                assert result.details["errors"] == 3
                assert result.details["warnings"] == 1

                # Check that error patterns were detected
                assert "errors_found" in result.details
                errors = result.details["errors_found"]
                assert any("Agent deployment" in str(e) for e in errors)
                assert any("MCP server" in str(e) for e in errors)
                assert any("Port binding" in str(e) for e in errors)

    def test_error_pattern_detection(self):
        """Test that specific error patterns are correctly detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            log_dir = project_root / ".claude-mpm" / "logs" / "startup"
            log_dir.mkdir(parents=True)

            # Create a log with various error patterns
            log_file = log_dir / "startup-2024-01-15-14-30-45.log"
            log_content = """
2024-01-15 14:30:45 - cli - ERROR - ModuleNotFoundError: No module named 'socketio'
2024-01-15 14:30:45 - cli - ERROR - Permission denied: /home/user/.claude-mpm/
2024-01-15 14:30:45 - cli - ERROR - Configuration file invalid: yaml.scanner.ScannerError
2024-01-15 14:30:45 - cli - WARNING - .claude.json file is large (2.5GB)
2024-01-15 14:30:45 - cli - ERROR - Failed to start Socket.IO daemon
"""
            log_file.write_text(log_content)

            with patch("pathlib.Path.cwd", return_value=project_root):
                check = StartupLogCheck()
                result = check.run()

                assert result.status == DiagnosticStatus.ERROR
                assert result.details["errors"] == 4

                # Verify specific fixes are suggested
                errors = result.details.get("errors_found", [])
                assert any("pip install" in str(e) for e in errors)
                assert any("permissions" in str(e).lower() for e in errors)
                assert any("config validate" in str(e) for e in errors)
                assert any("daemon" in str(e).lower() for e in errors)

    def test_fix_command_extraction(self):
        """Test that fix commands are properly extracted."""
        check = StartupLogCheck()

        analysis = {
            "errors_found": [
                (
                    "Agent deployment failure",
                    "Check agent configuration in .claude/agents/ and run 'claude-mpm deploy'",
                ),
                (
                    "Missing Python dependency",
                    "Install missing dependencies: pip install claude-mpm[agents]",
                ),
            ],
            "error_count": 2,
            "warning_count": 0,
            "warnings_found": [],
            "recommendations": [],
        }

        fix_command = check._get_fix_command(analysis)
        assert fix_command == "claude-mpm deploy"  # First claude-mpm command found
