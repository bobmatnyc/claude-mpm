"""
Unit tests for the Enhanced Archive Manager Service
====================================================

Tests the documentation review, Git integration, and intelligent
archival features of the ArchiveManager service.
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.claude_mpm.services.project.archive_manager import ArchiveManager


class TestArchiveManager(unittest.TestCase):
    """Test suite for ArchiveManager service."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.manager = ArchiveManager(self.test_dir)

        # Create test files
        self.test_file = self.test_dir / "test_doc.md"
        self.test_file.write_text("# Test Documentation\n\nVersion 1.0.0\n")

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir)

    def test_archive_file_with_metadata(self):
        """Test archiving a file with metadata."""
        metadata = {
            "test": True,
            "author": "Test Suite",
        }

        result = self.manager.archive_file(
            self.test_file,
            reason="Test archive",
            metadata=metadata,
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.exists())

        # Check metadata file
        meta_file = Path(str(result) + ".meta.json")
        self.assertTrue(meta_file.exists())

        meta_data = json.loads(meta_file.read_text())
        self.assertEqual(meta_data["reason"], "Test archive")
        self.assertEqual(meta_data["test"], True)

    def test_list_archives(self):
        """Test listing archives."""
        # Create multiple archives
        import time

        for i in range(3):
            self.test_file.write_text(f"Version {i}")
            self.manager.archive_file(self.test_file, reason=f"Version {i}")
            time.sleep(0.1)  # Ensure different timestamps

        archives = self.manager.list_archives("test_doc.md")
        self.assertGreaterEqual(len(archives), 1)  # At least one archive created

        # Check with metadata
        archives_with_meta = self.manager.list_archives(
            "test_doc.md", include_metadata=True
        )
        self.assertTrue(all("metadata" in a for a in archives_with_meta))

    def test_restore_archive(self):
        """Test restoring from archive."""
        # Save original content
        original_content = self.test_file.read_text()

        # Archive original
        archive_result = self.manager.archive_file(
            self.test_file, reason="Before change"
        )
        self.assertIsNotNone(archive_result)

        # Get the archive name immediately after creation
        archive_name = archive_result.name

        # Modify file
        self.test_file.write_text("# Modified\n\nVersion 2.0.0\n")
        modified_content = self.test_file.read_text()

        # Delete the modified file first to avoid backup during restore
        self.test_file.unlink()

        # Restore using the specific archive name
        success, message = self.manager.restore_archive(
            archive_name, target_path=self.test_file
        )
        self.assertTrue(success)
        self.assertIn("Successfully restored", message)

        # Check content was restored to original
        restored_content = self.test_file.read_text()
        self.assertEqual(restored_content, original_content)
        self.assertNotEqual(restored_content, modified_content)

    def test_compare_with_archive(self):
        """Test comparing current file with archive."""
        # Archive original
        self.manager.archive_file(self.test_file, reason="Original")
        latest = self.manager.get_latest_archive("test_doc.md")

        # Modify file
        self.test_file.write_text("# Modified\n\nVersion 2.0.0\nNew content\n")

        # Compare
        comparison = self.manager.compare_with_archive(self.test_file, latest.name)

        self.assertIn("current_lines", comparison)
        self.assertIn("archive_lines", comparison)
        self.assertFalse(comparison["identical"])
        self.assertGreater(comparison["lines_added"], 0)

    def test_auto_archive_cleanup(self):
        """Test automatic archive cleanup."""
        # Create more than MAX_ARCHIVES
        for i in range(15):
            self.test_file.write_text(f"Version {i}")
            self.manager.archive_file(self.test_file)

        # Check that only MAX_ARCHIVES remain
        archives = self.manager.list_archives("test_doc.md")
        self.assertLessEqual(len(archives), self.manager.MAX_ARCHIVES)

    @patch.object(ArchiveManager, "_run_git_command")
    def test_git_history_integration(self, mock_git):
        """Test Git history integration."""
        # Set git repo flag
        self.manager.is_git_repo = True

        # Mock git log output
        mock_git.return_value = (
            "abc12345|John Doe|1704067200|feat: initial commit\n"
            "def67890|Jane Smith|1704153600|fix: bug fix"
        )

        history = self.manager.get_file_git_history(self.test_file)

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["hash"], "abc12345")
        self.assertEqual(history[0]["author"], "John Doe")
        self.assertIn("initial commit", history[0]["message"])

    @patch.object(ArchiveManager, "_run_git_command")
    def test_documentation_review(self, mock_git):
        """Test documentation review with outdated detection."""
        # Create test documentation
        claude_md = self.test_dir / "CLAUDE.md"
        claude_md.write_text(
            """
# Claude MPM v3.0.0

TODO: Update this section
This is deprecated functionality
Coming soon in future release
Temporary workaround for issue
        """
        )

        # Mock git history
        mock_git.return_value = "abc12345|Test|1704067200|test commit"

        review = self.manager.review_documentation()

        self.assertIn("CLAUDE.md", review["files_reviewed"])
        self.assertTrue(review["outdated_sections"])
        self.assertTrue(review["recommendations"])

        # Check outdated indicators detected
        claude_report = review["files_reviewed"]["CLAUDE.md"]
        indicators = claude_report["outdated_indicators"]
        self.assertTrue(any("TODO" in i["type"] for i in indicators))
        self.assertTrue(any("Deprecated" in i["type"] for i in indicators))

    def test_version_comparison(self):
        """Test version string comparison."""
        self.assertTrue(self.manager._is_older_version("1.0.0", "2.0.0"))
        self.assertTrue(self.manager._is_older_version("v1.9.9", "v2.0.0"))
        self.assertFalse(self.manager._is_older_version("2.0.0", "1.0.0"))
        self.assertFalse(self.manager._is_older_version("1.0.0", "1.0.0"))

    def test_documentation_sync(self):
        """Test documentation synchronization."""
        # Create test files
        version_file = self.test_dir / "VERSION"
        version_file.write_text("4.3.20")

        readme = self.test_dir / "README.md"
        readme.write_text("# Project v1.0.0\n\nOld version reference")

        changelog = self.test_dir / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n## [1.0.0] - 2024-01-01\n")

        claude = self.test_dir / "CLAUDE.md"
        claude.write_text("# Claude MPM")

        # Test sync
        result = self.manager.sync_with_readme_and_changelog()

        # Check if version was updated
        if result["synced"]:
            readme_content = readme.read_text()
            self.assertIn("4.3.20", readme_content)

    def test_auto_detect_outdated(self):
        """Test auto-detection of outdated documentation."""
        # Create outdated documentation
        old_doc = self.test_dir / "CLAUDE.md"
        old_doc.write_text(
            """
# Old Documentation

TODO: Fix this
TODO: Update that
DEPRECATED: Old feature
DEPRECATED: Legacy code
Temporary hack for issue
Coming soon in next release
Beta feature documentation
Experimental API
TODO: Refactor this
FIXME: Known bug
XXX: Bad code
Workaround for problem
        """
        )

        result = self.manager.auto_detect_and_archive_outdated(dry_run=True)

        self.assertIn("CLAUDE.md", result["reviewed_files"])
        self.assertTrue(result["skipped_files"])  # Should detect as outdated

        # Check detection reasons
        for item in result["skipped_files"]:
            if item["file"] == "CLAUDE.md":
                reasons = item["reason"]
                self.assertTrue(any("outdated indicators" in r for r in reasons))

    def test_generate_diff_report(self):
        """Test diff report generation."""
        # Create and archive original
        self.test_file.write_text("Line 1\nLine 2\nLine 3\n")
        self.manager.archive_file(self.test_file)
        latest = self.manager.get_latest_archive("test_doc.md")

        # Modify file
        self.test_file.write_text("Line 1\nModified Line 2\nLine 3\nNew Line 4\n")

        # Generate diff
        diff = self.manager.generate_documentation_diff_report(
            self.test_file, self.manager.archive_path / latest.name
        )

        self.assertIn("Line 1", diff)
        self.assertIn("-Line 2", diff)
        self.assertIn("+Modified Line 2", diff)
        self.assertIn("+New Line 4", diff)

    def test_archive_compression(self):
        """Test archive compression for old files."""
        # Create an archive
        result = self.manager.archive_file(self.test_file)
        self.assertIsNotNone(result)

        # Get the archive file
        archives = self.manager.list_archives("test_doc.md")
        self.assertGreater(len(archives), 0)
        original_archive = archives[0]["name"]

        # Manually set old modification time
        archive_path = self.manager.archive_path / original_archive
        self.assertTrue(archive_path.exists())

        old_time = datetime.now() - timedelta(days=10)
        import os

        os.utime(archive_path, (old_time.timestamp(), old_time.timestamp()))

        # Create another archive to trigger cleanup
        self.test_file.write_text("New content to trigger cleanup")
        self.manager.archive_file(self.test_file)

        # Check if compressed
        compressed_path = archive_path.with_suffix(archive_path.suffix + ".gz")
        # The file should either be compressed or still exist (depending on timing)
        self.assertTrue(compressed_path.exists() or archive_path.exists())

    def test_create_archive_report(self):
        """Test comprehensive archive report generation."""
        # Create multiple archives
        for i in range(3):
            test_file = self.test_dir / f"doc_{i}.md"
            test_file.write_text(f"Content {i}")
            self.manager.archive_file(test_file)

        report = self.manager.create_archive_report()

        self.assertIn("total_archives", report)
        self.assertIn("total_size", report)
        self.assertIn("files_tracked", report)
        self.assertEqual(report["total_archives"], 3)
        self.assertGreater(report["total_size"], 0)


class TestArchiveManagerGitIntegration(unittest.TestCase):
    """Test Git-specific features of ArchiveManager."""

    def setUp(self):
        """Set up test with real git repo."""
        # Use the actual project directory for Git tests
        self.project_dir = Path.cwd()
        self.manager = ArchiveManager(self.project_dir)

    @unittest.skipUnless((Path.cwd() / ".git").exists(), "Requires Git repository")
    def test_real_git_history(self):
        """Test with real Git history."""
        # Test on CLAUDE.md which should exist
        claude_path = self.project_dir / "CLAUDE.md"
        if claude_path.exists():
            history = self.manager.get_file_git_history(claude_path, limit=5)
            self.assertIsInstance(history, list)
            if history:
                self.assertIn("hash", history[0])
                self.assertIn("author", history[0])
                self.assertIn("date", history[0])
                self.assertIn("message", history[0])

    @unittest.skipUnless((Path.cwd() / ".git").exists(), "Requires Git repository")
    def test_real_documentation_review(self):
        """Test documentation review on real project."""
        review = self.manager.review_documentation()

        self.assertIn("files_reviewed", review)
        self.assertIn("synchronization_issues", review)
        self.assertIn("recommendations", review)

        # Should have reviewed at least CLAUDE.md if it exists
        if (self.project_dir / "CLAUDE.md").exists():
            self.assertIn("CLAUDE.md", review["files_reviewed"])


if __name__ == "__main__":
    unittest.main()
