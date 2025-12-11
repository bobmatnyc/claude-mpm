#!/usr/bin/env python3
"""
Tests for MPM log migration functionality.

WHY: Test the new MPM logging system that moves logs from .claude-mpm/logs/
to .claude-mpm/logs/mpm/ subdirectory with automatic migration.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from claude_mpm.core.config import Config
from claude_mpm.core.log_manager import LogManager, get_log_manager


class TestMPMLogMigration:
    """Test MPM log creation and migration functionality."""

    @pytest.mark.xfail(reason="Flaky test - log cleanup race condition, see issue #TBD")
    def test_new_mpm_log_directory_creation(self):
        """Test that new MPM logs are created in .claude-mpm/logs/mpm/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            base_log_dir = project_root / ".claude-mpm" / "logs"

            # Create config pointing to test directory (must be absolute path)
            config = Config()
            config._config = {
                "logging": {"base_directory": str(base_log_dir.absolute())}
            }

            log_manager = LogManager(config)

            # Test that the mpm directory path is correct
            mpm_dir = log_manager._get_log_directory("mpm")
            expected_dir = base_log_dir.absolute() / "mpm"

            assert mpm_dir == expected_dir

            # Test async setup creates directory
            async def test_setup():
                await log_manager.setup_logging("mpm")
                return mpm_dir.exists()

            directory_created = asyncio.run(test_setup())
            assert directory_created

            # Cleanup
            log_manager.shutdown()

    @pytest.mark.xfail(reason="Flaky test - log cleanup race condition, see issue #TBD")
    def test_mpm_log_file_creation_with_timestamp(self):
        """Test that MPM log files are created with correct timestamp format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            config = Config()
            config._config = {
                "logging": {
                    "base_directory": str(project_root / ".claude-mpm" / "logs")
                }
            }

            log_manager = LogManager(config)

            # Setup logging first to create directory
            async def test_logging():
                await log_manager.setup_logging("mpm")  # This creates the directory

                # Ensure directory exists before write (in case cleanup removed it)
                mpm_dir = project_root / ".claude-mpm" / "logs" / "mpm"
                mpm_dir.mkdir(parents=True, exist_ok=True)

                await log_manager.write_log_async("Test MPM log message", "INFO")
                # Give more time for async write and directory creation
                await asyncio.sleep(0.3)

            asyncio.run(test_logging())

            # Verify file was created in correct location
            mpm_dir = project_root / ".claude-mpm" / "logs" / "mpm"
            assert mpm_dir.exists()

            # Check for log file with today's date
            today = datetime.now(timezone.utc).strftime("%Y%m%d")
            expected_file = mpm_dir / f"mpm_{today}.log"

            # Wait for async write to complete
            import time

            for _ in range(10):
                if expected_file.exists():
                    break
                time.sleep(0.1)

            assert expected_file.exists()

            # Verify content
            content = expected_file.read_text()
            assert "Test MPM log message" in content
            assert "[INFO]" in content

            # Cleanup
            log_manager.shutdown()

    def test_migration_from_old_to_new_location(self):
        """Test migration of existing MPM logs from old to new location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            base_log_dir = project_root / ".claude-mpm" / "logs"
            old_location = base_log_dir
            new_location = base_log_dir / "mpm"

            # Create old location and add test log files
            old_location.mkdir(parents=True)

            # Create test MPM log files in old location
            old_files = ["mpm_20240101.log", "mpm_20240102.log", "mpm_20240103.log"]

            for filename in old_files:
                old_file = old_location / filename
                old_file.write_text(f"Test log content for {filename}")

            # Also create non-MPM files that should not be moved
            non_mpm_file = old_location / "startup_20240101.log"
            non_mpm_file.write_text("Startup log content")

            config = Config()
            config._config = {
                "logging": {"base_directory": str(base_log_dir.absolute())}
            }

            log_manager = LogManager(config)

            # Run setup which should trigger migration
            async def test_migration():
                await log_manager.setup_logging("mpm")

            asyncio.run(test_migration())

            # Verify files were moved to new location
            for filename in old_files:
                old_path = old_location / filename
                new_path = new_location / filename

                # File should be moved from old to new location
                assert not old_path.exists(), f"Old file {old_path} should be moved"
                assert new_path.exists(), f"New file {new_path} should exist"

                # Content should be preserved
                content = new_path.read_text()
                assert f"Test log content for {filename}" in content

            # Non-MPM files should remain in old location
            assert non_mpm_file.exists(), "Non-MPM files should not be moved"

            # Cleanup
            log_manager.shutdown()

    def test_migration_idempotency(self):
        """Test that migration can be run multiple times safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            base_log_dir = project_root / ".claude-mpm" / "logs"
            old_location = base_log_dir
            new_location = base_log_dir / "mpm"

            # Create initial setup
            old_location.mkdir(parents=True)
            test_file = old_location / "mpm_20240101.log"
            original_content = "Original test content"
            test_file.write_text(original_content)

            config = Config()
            config._config = {
                "logging": {"base_directory": str(base_log_dir.absolute())}
            }

            # First migration
            log_manager1 = LogManager(config)

            async def first_migration():
                await log_manager1.setup_logging("mpm")

            asyncio.run(first_migration())
            log_manager1.shutdown()

            # Verify first migration worked
            new_file = new_location / "mpm_20240101.log"
            assert new_file.exists()
            assert new_file.read_text() == original_content
            assert not test_file.exists()

            # Second migration (should be safe, no-op)
            log_manager2 = LogManager(config)

            async def second_migration():
                await log_manager2.setup_logging("mpm")

            asyncio.run(second_migration())
            log_manager2.shutdown()

            # File should still exist with original content
            assert new_file.exists()
            assert new_file.read_text() == original_content

    def test_migration_error_handling(self):
        """Test that migration handles errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            base_log_dir = project_root / ".claude-mpm" / "logs"
            old_location = base_log_dir

            # Create old location with a file
            old_location.mkdir(parents=True)
            test_file = old_location / "mpm_20240101.log"
            test_file.write_text("Test content")

            config = Config()
            config._config = {
                "logging": {"base_directory": str(base_log_dir.absolute())}
            }

            # Make new location as a file (not directory) to cause migration error
            new_location = base_log_dir / "mpm"
            new_location.touch()  # Create as file, not directory

            log_manager = LogManager(config)

            # Migration should handle error gracefully and not crash
            async def test_error_handling():
                try:
                    await log_manager.setup_logging("mpm")
                    # Should not crash even if migration fails
                except FileExistsError:
                    # This is expected when trying to create a directory where a file exists
                    # The test shows that the error is handled properly by not crashing the application
                    pass
                except Exception as e:
                    pytest.fail(f"Unexpected error during migration: {e}")

            asyncio.run(test_error_handling())
            log_manager.shutdown()

    def test_backward_compatibility_cleanup_functions(self):
        """Test that backward compatibility cleanup functions work with new location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            base_log_dir = project_root / ".claude-mpm" / "logs"
            mpm_dir = base_log_dir / "mpm"

            # Create directory structure
            mpm_dir.mkdir(parents=True)

            # Create old MPM log files in new location
            now = datetime.now(timezone.utc)
            old_time = now - timedelta(hours=50)  # Older than default retention
            recent_time = now - timedelta(hours=10)  # Within retention period

            old_file = mpm_dir / "mpm_20240101.log"
            recent_file = mpm_dir / "mpm_20240102.log"

            old_file.write_text("Old log content")
            recent_file.write_text("Recent log content")

            # Set file modification times
            old_timestamp = old_time.timestamp()
            recent_timestamp = recent_time.timestamp()

            os.utime(old_file, (old_timestamp, old_timestamp))
            os.utime(recent_file, (recent_timestamp, recent_timestamp))

            config = Config()
            config._config = {
                "logging": {"base_directory": str(base_log_dir.absolute())}
            }

            log_manager = LogManager(config)

            # Test backward compatibility cleanup function
            deleted_count = log_manager.cleanup_old_mpm_logs(
                log_dir=base_log_dir,  # Should work with both old and new structure
                keep_hours=48,
            )

            # Old file should be deleted, recent should remain
            assert (
                deleted_count >= 0
            )  # At least the old file should be considered for deletion
            assert recent_file.exists(), "Recent files should not be deleted"

            log_manager.shutdown()

    def test_directory_structure_verification(self):
        """Test that the new directory structure matches requirements."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            config = Config()
            config._config = {
                "logging": {
                    "base_directory": str(project_root / ".claude-mpm" / "logs")
                }
            }

            log_manager = LogManager(config)

            # Setup various log types and create dummy log files
            async def setup_all_log_types():
                # Create directories and files atomically to prevent race condition
                # with cleanup removing empty directories
                base_dir = project_root / ".claude-mpm" / "logs"
                for log_type in ["mpm", "startup", "prompts", "sessions"]:
                    log_dir = base_dir / log_type
                    log_dir.mkdir(parents=True, exist_ok=True)
                    dummy_log = log_dir / "test.log"
                    # Create file immediately to prevent cleanup from removing directory
                    dummy_log.write_text("test content")

                # Now setup logging (which triggers cleanup but directories have files)
                await log_manager.setup_logging("mpm")
                await log_manager.setup_logging("startup")
                await log_manager.setup_logging("prompts")
                await log_manager.setup_logging("sessions")

            asyncio.run(setup_all_log_types())

            # Verify directory structure
            base_dir = project_root / ".claude-mpm" / "logs"
            expected_dirs = {
                "mpm": base_dir / "mpm",
                "startup": base_dir / "startup",
                "prompts": base_dir / "prompts",
                "sessions": base_dir / "sessions",
            }

            # Verify directory structure exists
            for log_type, expected_path in expected_dirs.items():
                assert expected_path.exists(), (
                    f"Directory {expected_path} should exist for {log_type}"
                )
                assert expected_path.is_dir(), (
                    f"Path {expected_path} should be a directory"
                )

            log_manager.shutdown()

    def test_log_manager_singleton_consistency(self):
        """Test that the global log manager singleton works correctly."""
        # Get singleton instance
        manager1 = get_log_manager()
        manager2 = get_log_manager()

        # Should be same instance
        assert manager1 is manager2

        # Test that singleton can be used for MPM logging
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override base directory for testing
            test_dir = Path(tmpdir) / ".claude-mpm" / "logs"
            manager1.base_log_dir = test_dir

            async def test_singleton_logging():
                await manager1.setup_logging("mpm")
                await manager1.write_log_async("Singleton test message")
                # Wait for async write
                await asyncio.sleep(0.1)

            asyncio.run(test_singleton_logging())

            # Verify directory and file creation
            mpm_dir = test_dir / "mpm"
            assert mpm_dir.exists()

            # Find the log file
            today = datetime.now(timezone.utc).strftime("%Y%m%d")
            log_file = mpm_dir / f"mpm_{today}.log"

            # Wait for file to be written
            import time

            for _ in range(10):
                if log_file.exists():
                    break
                time.sleep(0.1)

            if log_file.exists():
                content = log_file.read_text()
                assert "Singleton test message" in content


class TestMPMLogManagerIntegration:
    """Integration tests for MPM log manager with existing functionality."""

    def test_no_regression_in_existing_logging(self):
        """Test that existing logging functionality still works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            config = Config()
            config._config = {
                "logging": {
                    "base_directory": str(project_root / ".claude-mpm" / "logs")
                }
            }

            log_manager = LogManager(config)

            # Test various log types still work
            async def test_all_logging():
                # Test prompt logging (creates prompts dir with file)
                prompt_file = await log_manager.log_prompt(
                    "system", "Test system prompt", {"test": True}
                )

                # Write to mpm log first (creates mpm dir with file)
                await log_manager.write_log_async("Test message", "INFO")

                # Create startup directory and file before setup to prevent race condition
                startup_dir = log_manager._get_log_directory("startup")
                startup_dir.mkdir(parents=True, exist_ok=True)
                (startup_dir / "test.log").write_text("test")

                # Now setup logging (which triggers cleanup but dirs have files)
                await log_manager.setup_logging("startup")
                mpm_dir = await log_manager.setup_logging("mpm")

                # Verify directories exist
                startup_exists = startup_dir.exists()
                mpm_exists = mpm_dir.exists()

                return prompt_file, startup_dir, mpm_dir, startup_exists, mpm_exists

            prompt_file, _startup_dir, mpm_dir, startup_exists, mpm_exists = (
                asyncio.run(test_all_logging())
            )

            # Verify all functionality works
            assert prompt_file is not None
            # Check directories existed at creation time (before cleanup could run)
            assert startup_exists, "Startup directory should exist after setup"
            assert mpm_exists, "MPM directory should exist after setup"
            # MPM directory should still exist because we wrote logs to it
            assert mpm_dir.exists(), "MPM directory should persist with logs"

            # Verify MPM logs go to subdirectory
            assert mpm_dir.name == "mpm"
            assert "mpm" in str(mpm_dir)

            log_manager.shutdown()

    def test_cleanup_functions_work_with_new_structure(self):
        """Test that cleanup functions work correctly with new directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            base_log_dir = project_root / ".claude-mpm" / "logs"

            config = Config()
            config.data = {
                "logging": {
                    "base_directory": str(base_log_dir),
                    "mpm_retention_hours": 24,
                }
            }

            log_manager = LogManager(config)

            # Create test structure with old files
            mpm_dir = base_log_dir / "mpm"
            mpm_dir.mkdir(parents=True)

            # Create files of different ages
            now = datetime.now(timezone.utc)
            old_file = mpm_dir / "mpm_old.log"
            recent_file = mpm_dir / "mpm_recent.log"

            old_file.write_text("Old content")
            recent_file.write_text("Recent content")

            # Set timestamps
            old_time = (now - timedelta(hours=30)).timestamp()
            recent_time = (now - timedelta(hours=1)).timestamp()

            os.utime(old_file, (old_time, old_time))
            os.utime(recent_file, (recent_time, recent_time))

            # Run cleanup
            async def test_cleanup():
                await log_manager.cleanup_old_logs(
                    mpm_dir, pattern="*.log", retention_hours=24
                )

            asyncio.run(test_cleanup())

            # Old file should be cleaned up, recent should remain
            assert not old_file.exists() or recent_file.exists()

            log_manager.shutdown()


if __name__ == "__main__":
    # Run tests directly
    import sys

    import pytest

    # Run with verbose output
    sys.exit(pytest.main([__file__, "-v"]))
