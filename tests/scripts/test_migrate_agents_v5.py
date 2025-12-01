"""Tests for v5.0 agent migration script."""

import shutil
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.migrate_agents_v5 import AgentMigrator


@pytest.fixture
def migrator(tmp_path):
    """Create AgentMigrator with temp directory."""
    migrator = AgentMigrator(dry_run=False, force=True)

    # Override paths to use temp directory
    migrator.agents_dir = tmp_path / ".claude" / "agents"
    migrator.archive_path = tmp_path / ".claude" / "agents-old-archive.zip"

    # Create directory
    migrator.agents_dir.mkdir(parents=True, exist_ok=True)

    return migrator


@pytest.fixture
def mock_agents():
    """Return list of mock agent filenames."""
    return ["engineer_agent.md", "qa_agent.md", "research_agent.md", "pm_agent.md"]


class TestAgentMigrator:
    """Test AgentMigrator class."""

    def test_find_old_agents_empty_directory(self, migrator):
        """Test finding agents in empty directory."""
        agents = migrator.find_old_agents()
        assert agents == []

    def test_find_old_agents_with_agents(self, migrator, mock_agents):
        """Test finding old agents."""
        # Create agents in temp directory
        for agent in mock_agents:
            (migrator.agents_dir / agent).write_text("old content")

        agents = migrator.find_old_agents()
        assert len(agents) == len(mock_agents)

        # Verify all expected agents found
        agent_names = {a.name for a in agents}
        assert agent_names == set(mock_agents)

    def test_is_git_sourced_agent_false(self, migrator):
        """Test identifying non-Git-sourced agent."""
        agent_path = migrator.agents_dir / "old_agent.md"
        agent_path.write_text("# Old Agent\n\nNo Git metadata")

        assert not migrator.is_git_sourced_agent(agent_path)

    def test_is_git_sourced_agent_true(self, migrator):
        """Test identifying Git-sourced agent."""
        agent_path = migrator.agents_dir / "git_agent.md"
        agent_path.write_text("# Git Agent\n\ngit_source: true")

        assert migrator.is_git_sourced_agent(agent_path)

    def test_create_archive_readme(self, migrator):
        """Test README generation."""
        agents = [Path("agent1.md"), Path("agent2.md"), Path("agent3.md")]

        readme = migrator.create_archive_readme(agents)

        # Verify content
        assert "Claude MPM v5.0 Agent Migration Archive" in readme
        assert "Agents Archived: 3" in readme
        assert "agent1.md" in readme
        assert "agent2.md" in readme
        assert "agent3.md" in readme
        assert "bobmatnyc/claude-mpm-agents" in readme

    def test_create_archive_success(self, migrator, mock_agents):
        """Test successful archive creation."""
        # Create agents
        for agent in mock_agents:
            (migrator.agents_dir / agent).write_text(f"Content of {agent}")

        agents = migrator.find_old_agents()

        # Create archive
        success = migrator.create_archive(agents)
        assert success

        # Verify archive exists
        assert migrator.archive_path.exists()

        # Verify archive contents
        with zipfile.ZipFile(migrator.archive_path, "r") as zf:
            namelist = zf.namelist()

            # Check README
            assert "README.txt" in namelist

            # Check all agents archived
            for agent in mock_agents:
                assert f"agents/{agent}" in namelist

    def test_create_archive_dry_run(self, migrator, mock_agents):
        """Test dry-run mode doesn't create archive."""
        migrator.dry_run = True

        # Create agents
        for agent in mock_agents:
            (migrator.agents_dir / agent).write_text(f"Content of {agent}")

        agents = migrator.find_old_agents()

        # Create archive (dry run)
        success = migrator.create_archive(agents)
        assert success

        # Verify archive NOT created
        assert not migrator.archive_path.exists()

    def test_verify_archive_success(self, migrator, mock_agents):
        """Test archive verification success."""
        # Create agents
        for agent in mock_agents:
            (migrator.agents_dir / agent).write_text(f"Content of {agent}")

        agents = migrator.find_old_agents()

        # Create archive
        migrator.create_archive(agents)

        # Verify
        assert migrator.verify_archive(agents)

    def test_verify_archive_missing_files(self, migrator):
        """Test archive verification with missing files."""
        # Create incomplete archive
        with zipfile.ZipFile(migrator.archive_path, "w") as zf:
            zf.writestr("README.txt", "test")
            zf.writestr("agents/agent1.md", "content")

        # Try to verify with more agents
        agents = [
            Path("agent1.md"),
            Path("agent2.md"),  # This one is missing
        ]

        assert not migrator.verify_archive(agents)

    def test_remove_old_agents_success(self, migrator, mock_agents):
        """Test successful agent removal."""
        # Create agents
        for agent in mock_agents:
            (migrator.agents_dir / agent).write_text(f"Content of {agent}")

        agents = migrator.find_old_agents()

        # Remove agents
        removed = migrator.remove_old_agents(agents)
        assert removed == len(mock_agents)

        # Verify all removed
        for agent in mock_agents:
            assert not (migrator.agents_dir / agent).exists()

    def test_remove_old_agents_dry_run(self, migrator, mock_agents):
        """Test dry-run doesn't remove agents."""
        migrator.dry_run = True

        # Create agents
        for agent in mock_agents:
            (migrator.agents_dir / agent).write_text(f"Content of {agent}")

        agents = migrator.find_old_agents()

        # Remove agents (dry run)
        removed = migrator.remove_old_agents(agents)
        assert removed == len(mock_agents)

        # Verify NOT removed
        for agent in mock_agents:
            assert (migrator.agents_dir / agent).exists()

    @patch("subprocess.run")
    def test_deploy_git_agents_success(self, mock_run, migrator):
        """Test successful Git agent deployment."""
        # Mock successful deployment
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Deployed 47 agents successfully"
        )

        success, count = migrator.deploy_git_agents()

        assert success
        assert count == 47

        # Verify subprocess called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["claude-mpm", "agent-source", "sync"]

    @patch("subprocess.run")
    def test_deploy_git_agents_failure(self, mock_run, migrator):
        """Test Git agent deployment failure."""
        # Mock failed deployment
        mock_run.return_value = MagicMock(
            returncode=1, stderr="Deployment failed: network error"
        )

        success, count = migrator.deploy_git_agents()

        assert not success
        assert count == 0

    @patch("subprocess.run")
    def test_deploy_git_agents_dry_run(self, mock_run, migrator):
        """Test dry-run doesn't deploy agents."""
        migrator.dry_run = True

        success, count = migrator.deploy_git_agents()

        assert success
        assert count == 0

        # Verify subprocess NOT called
        mock_run.assert_not_called()

    def test_confirm_migration_force(self, migrator):
        """Test forced confirmation."""
        migrator.force = True

        assert migrator.confirm_migration([])

    @patch("builtins.input", return_value="y")
    def test_confirm_migration_yes(self, mock_input, migrator):
        """Test user confirms migration."""
        migrator.force = False

        assert migrator.confirm_migration([Path("agent1.md")])

    @patch("builtins.input", return_value="n")
    def test_confirm_migration_no(self, mock_input, migrator):
        """Test user rejects migration."""
        migrator.force = False

        assert not migrator.confirm_migration([Path("agent1.md")])

    @patch("subprocess.run")
    def test_run_no_agents(self, mock_run, migrator):
        """Test migration with no old agents."""
        # Mock Git sync
        mock_run.return_value = MagicMock(returncode=0, stdout="Synced 47 agents")

        exit_code = migrator.run()

        assert exit_code == 0

    @patch("subprocess.run")
    def test_run_with_agents_success(self, mock_run, migrator, mock_agents):
        """Test successful migration."""
        # Create agents
        for agent in mock_agents:
            (migrator.agents_dir / agent).write_text(f"Content of {agent}")

        # Mock Git sync
        mock_run.return_value = MagicMock(returncode=0, stdout="Deployed 47 agents")

        exit_code = migrator.run()

        assert exit_code == 0

        # Verify archive created
        assert migrator.archive_path.exists()

        # Verify agents removed
        for agent in mock_agents:
            assert not (migrator.agents_dir / agent).exists()

    def test_run_user_cancels(self, migrator, mock_agents):
        """Test migration cancelled by user."""
        migrator.force = False

        # Create agents
        for agent in mock_agents:
            (migrator.agents_dir / agent).write_text(f"Content of {agent}")

        # Mock user input
        with patch("builtins.input", return_value="n"):
            exit_code = migrator.run()

        assert exit_code == 1

        # Verify nothing changed
        for agent in mock_agents:
            assert (migrator.agents_dir / agent).exists()

        assert not migrator.archive_path.exists()


class TestArchiveIntegrity:
    """Test archive creation and integrity."""

    def test_archive_can_be_extracted(self, migrator, mock_agents):
        """Test archive can be extracted."""
        # Create agents
        for agent in mock_agents:
            (migrator.agents_dir / agent).write_text(f"Content of {agent}")

        agents = migrator.find_old_agents()

        # Create archive
        migrator.create_archive(agents)

        # Extract to temp directory
        with tempfile.TemporaryDirectory() as extract_dir:
            with zipfile.ZipFile(migrator.archive_path, "r") as zf:
                zf.extractall(extract_dir)

            extract_path = Path(extract_dir)

            # Verify README
            readme = extract_path / "README.txt"
            assert readme.exists()
            assert "Claude MPM v5.0" in readme.read_text()

            # Verify agents
            agents_dir = extract_path / "agents"
            for agent in mock_agents:
                agent_file = agents_dir / agent
                assert agent_file.exists()
                assert f"Content of {agent}" in agent_file.read_text()

    def test_archive_compression(self, migrator, mock_agents):
        """Test archive uses compression."""
        # Create agents with repetitive content
        large_content = "x" * 10000
        for agent in mock_agents:
            (migrator.agents_dir / agent).write_text(large_content)

        agents = migrator.find_old_agents()

        # Create archive
        migrator.create_archive(agents)

        # Calculate compression ratio
        uncompressed_size = sum(
            (migrator.agents_dir / agent).stat().st_size for agent in mock_agents
        )
        compressed_size = migrator.archive_path.stat().st_size

        # Should achieve significant compression
        compression_ratio = compressed_size / uncompressed_size
        assert compression_ratio < 0.1  # At least 90% compression


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
