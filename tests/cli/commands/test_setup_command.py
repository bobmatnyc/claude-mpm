"""Tests for setup command with kuzu-memory migration archival."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.cli.commands.setup import SetupCommand


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with mock memory files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create .claude-mpm/memories directory
        memories_dir = project_dir / ".claude-mpm" / "memories"
        memories_dir.mkdir(parents=True)

        # Create sample memory files
        (memories_dir / "agent1.md").write_text("# Agent 1 Memory\nSome content")
        (memories_dir / "agent2.md").write_text("# Agent 2 Memory\nMore content")
        (memories_dir / "agent3.md").write_text("# Agent 3 Memory\nExtra content")

        yield project_dir


class TestSetupKuzuMemoryArchival:
    """Test archival of memory files after kuzu-memory migration."""

    @patch("subprocess.run")
    @patch("importlib.util.find_spec")
    @patch("claude_mpm.cli.commands.setup.console")
    @patch("claude_mpm.cli.commands.setup.Path.cwd")
    def test_archives_migrated_files(
        self,
        mock_cwd,
        mock_console,
        mock_find_spec,
        mock_subprocess,
        temp_project_dir,
    ):
        """Test that migrated memory files are archived to .migrated/ directory."""
        # Setup mocks
        mock_cwd.return_value = temp_project_dir
        mock_find_spec.return_value = Mock()  # kuzu-memory installed
        mock_subprocess.return_value = Mock(returncode=0, stderr="")

        # Create setup command
        setup_cmd = SetupCommand()

        # Create mock args
        args = Mock(no_launch=True, force=False, upgrade=False)  # Don't launch after setup

        # Run setup
        result = setup_cmd._setup_kuzu_memory(args)

        # Verify success
        assert result.success

        # Check that archive directory was created
        archive_dir = temp_project_dir / ".claude-mpm" / "memories" / ".migrated"
        assert archive_dir.exists()
        assert archive_dir.is_dir()

        # Check that all memory files were moved to archive (excluding README.md)
        archived_files = [f for f in archive_dir.glob("*.md") if f.name != "README.md"]
        assert len(archived_files) == 3
        assert {f.name for f in archived_files} == {
            "agent1.md",
            "agent2.md",
            "agent3.md",
        }

        # Check that original memory files no longer exist in parent directory
        memories_dir = temp_project_dir / ".claude-mpm" / "memories"
        original_files = [
            f for f in memories_dir.glob("*.md") if not f.is_relative_to(archive_dir)
        ]
        assert len(original_files) == 0

        # Check that README was created
        readme = archive_dir / "README.md"
        assert readme.exists()
        readme_content = readme.read_text()
        assert "Migrated Memory Files" in readme_content
        assert "kuzu-memory" in readme_content
        assert "memories_backup" in readme_content

    @patch("subprocess.run")
    @patch("importlib.util.find_spec")
    @patch("claude_mpm.cli.commands.setup.console")
    @patch("claude_mpm.cli.commands.setup.Path.cwd")
    def test_backup_preserved_after_archival(
        self,
        mock_cwd,
        mock_console,
        mock_find_spec,
        mock_subprocess,
        temp_project_dir,
    ):
        """Test that backup directory is preserved after archival."""
        # Setup mocks
        mock_cwd.return_value = temp_project_dir
        mock_find_spec.return_value = Mock()
        mock_subprocess.return_value = Mock(returncode=0, stderr="")

        # Run setup
        setup_cmd = SetupCommand()
        args = Mock(no_launch=True, force=False, upgrade=False)
        result = setup_cmd._setup_kuzu_memory(args)

        assert result.success

        # Check backup directory exists
        backup_dir = temp_project_dir / ".claude-mpm" / "memories_backup"
        assert backup_dir.exists()

        # Check backup files exist
        backup_files = list(backup_dir.glob("*.md"))
        assert len(backup_files) == 3
        assert {f.name for f in backup_files} == {"agent1.md", "agent2.md", "agent3.md"}

    @patch("subprocess.run")
    @patch("importlib.util.find_spec")
    @patch("claude_mpm.cli.commands.setup.console")
    @patch("claude_mpm.cli.commands.setup.Path.cwd")
    def test_handles_archival_errors_gracefully(
        self,
        mock_cwd,
        mock_console,
        mock_find_spec,
        mock_subprocess,
        temp_project_dir,
    ):
        """Test that archival errors are handled gracefully without failing setup."""
        # Setup mocks
        mock_cwd.return_value = temp_project_dir
        mock_find_spec.return_value = Mock()
        mock_subprocess.return_value = Mock(returncode=0, stderr="")

        # Make one file read-only to cause archival error
        problem_file = temp_project_dir / ".claude-mpm" / "memories" / "agent2.md"
        problem_file.chmod(0o444)

        # Run setup
        setup_cmd = SetupCommand()
        args = Mock(no_launch=True, force=False, upgrade=False)

        # Setup should still succeed even if archival has issues
        result = setup_cmd._setup_kuzu_memory(args)
        assert result.success

    @patch("subprocess.run")
    @patch("importlib.util.find_spec")
    @patch("claude_mpm.cli.commands.setup.console")
    @patch("claude_mpm.cli.commands.setup.Path.cwd")
    def test_no_archival_when_no_migration(
        self,
        mock_cwd,
        mock_console,
        mock_find_spec,
        mock_subprocess,
        temp_project_dir,
    ):
        """Test that no archival occurs when no memory files are migrated."""
        # Setup mocks
        mock_cwd.return_value = temp_project_dir
        mock_find_spec.return_value = Mock()

        # Make migration fail for all files
        mock_subprocess.return_value = Mock(returncode=1, stderr="Migration failed")

        # Run setup
        setup_cmd = SetupCommand()
        args = Mock(no_launch=True, force=False, upgrade=False)
        result = setup_cmd._setup_kuzu_memory(args)

        # Setup should complete (kuzu-memory configured)
        assert result.success

        # Archive directory should not exist if no migration succeeded
        archive_dir = temp_project_dir / ".claude-mpm" / "memories" / ".migrated"
        # Archive dir might be created but should be empty
        if archive_dir.exists():
            assert len(list(archive_dir.glob("*.md"))) == 0

    @patch("subprocess.run")
    @patch("importlib.util.find_spec")
    @patch("claude_mpm.cli.commands.setup.console")
    @patch("claude_mpm.cli.commands.setup.Path.cwd")
    def test_archival_prevents_reimport(
        self,
        mock_cwd,
        mock_console,
        mock_find_spec,
        mock_subprocess,
        temp_project_dir,
    ):
        """Test that archived files won't be re-imported on subsequent setup runs."""
        # Setup mocks
        mock_cwd.return_value = temp_project_dir
        mock_find_spec.return_value = Mock()
        mock_subprocess.return_value = Mock(returncode=0, stderr="")

        # First setup run
        setup_cmd = SetupCommand()
        args = Mock(no_launch=True, force=False, upgrade=False)
        result1 = setup_cmd._setup_kuzu_memory(args)
        assert result1.success

        # Verify files are archived (excluding README.md)
        archive_dir = temp_project_dir / ".claude-mpm" / "memories" / ".migrated"
        archived_files = [f for f in archive_dir.glob("*.md") if f.name != "README.md"]
        assert len(archived_files) == 3

        # Verify no .md files in parent directory (except in .migrated)
        memories_dir = temp_project_dir / ".claude-mpm" / "memories"
        md_files_outside_archive = [
            f
            for f in memories_dir.glob("*.md")
            if not any(p.name == ".migrated" for p in f.parents)
        ]
        assert len(md_files_outside_archive) == 0

        # Second setup run - should not find any files to migrate
        result2 = setup_cmd._setup_kuzu_memory(args)
        assert result2.success

        # Mock should not have been called with learn for second run
        # (since no files to migrate)
        calls_with_learn = [
            call for call in mock_subprocess.call_args_list if "learn" in str(call)
        ]
        # Only first 3 migrations from first run
        assert len(calls_with_learn) == 3
