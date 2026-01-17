"""Integration tests for skill-source CLI commands.

WHY: These tests ensure that all skill-source commands work correctly end-to-end,
including argument parsing, command routing, error handling, and user-facing output.

DESIGN DECISION: Mock SkillSourceConfiguration and GitSkillSourceManager to avoid
actual Git operations during tests. Use temporary config files for isolation.
"""

import json
import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.cli.commands.skill_source import (
    _generate_source_id,
    handle_add_skill_source,
    handle_disable_skill_source,
    handle_enable_skill_source,
    handle_list_skill_sources,
    handle_remove_skill_source,
    handle_show_skill_source,
    handle_update_skill_sources,
    skill_source_command,
)
from claude_mpm.config.skill_sources import SkillSource


class TestGenerateSourceId:
    """Test source ID generation from URLs."""

    def test_https_url(self):
        """Test HTTPS URL parsing."""
        assert _generate_source_id("https://github.com/owner/repo") == "repo"
        assert _generate_source_id("https://github.com/owner/repo.git") == "repo"
        assert (
            _generate_source_id("https://github.com/owner/my-skills.git") == "my-skills"
        )

    def test_ssh_url(self):
        """Test SSH URL parsing."""
        assert _generate_source_id("git@github.com:owner/repo.git") == "repo"
        assert _generate_source_id("git@github.com:owner/repo") == "repo"

    def test_sanitization(self):
        """Test special character sanitization."""
        assert _generate_source_id("https://github.com/owner/my_repo") == "my_repo"
        assert _generate_source_id("https://github.com/owner/repo-name") == "repo-name"

    def test_edge_cases(self):
        """Test edge case URLs."""
        assert _generate_source_id("") == "unnamed-repo"
        assert _generate_source_id("invalid") == "invalid"


class TestSkillSourceCommand:
    """Test main command router."""

    def test_routes_to_add_handler(self, capsys):
        """Test routing to add command."""
        args = Namespace(skill_source_command="add")

        with patch(
            "claude_mpm.cli.commands.skill_source.handle_add_skill_source"
        ) as mock_add:
            mock_add.return_value = 0
            result = skill_source_command(args)

        assert result == 0
        mock_add.assert_called_once_with(args)

    def test_routes_to_list_handler(self):
        """Test routing to list command."""
        args = Namespace(skill_source_command="list")

        with patch(
            "claude_mpm.cli.commands.skill_source.handle_list_skill_sources"
        ) as mock_list:
            mock_list.return_value = 0
            result = skill_source_command(args)

        assert result == 0
        mock_list.assert_called_once_with(args)

    def test_unknown_command(self, capsys):
        """Test handling of unknown subcommand."""
        args = Namespace(skill_source_command="invalid")

        result = skill_source_command(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    def test_no_command(self, capsys):
        """Test handling when no subcommand provided."""
        args = Namespace(skill_source_command=None)

        result = skill_source_command(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    def test_handles_exceptions(self, capsys):
        """Test exception handling."""
        args = Namespace(skill_source_command="add")

        with patch(
            "claude_mpm.cli.commands.skill_source.handle_add_skill_source"
        ) as mock_add:
            mock_add.side_effect = Exception("Test error")
            result = skill_source_command(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Command failed" in captured.out


class TestHandleAddSkillSource:
    """Test add skill source command."""

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_add_source_success(self, mock_config_class, capsys):
        """Test successfully adding a new source."""
        # Setup mocks
        mock_config = Mock()
        mock_config.get_source.return_value = None  # Source doesn't exist
        mock_config.validate_priority_conflicts.return_value = {}
        mock_config_class.return_value = mock_config

        args = Namespace(
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            disabled=False,
            skip_test=True,  # Skip actual repository testing
            test=False,
        )

        result = handle_add_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Added skill source: repo" in captured.out
        assert "https://github.com/owner/repo" in captured.out
        assert "enabled" in captured.out
        mock_config.add_source.assert_called_once()

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_add_source_already_exists(self, mock_config_class, capsys):
        """Test adding a source that already exists."""
        # Setup mocks
        mock_config = Mock()
        existing_source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )
        mock_config.get_source.return_value = existing_source
        mock_config_class.return_value = mock_config

        args = Namespace(
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            disabled=False,
        )

        result = handle_add_skill_source(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "already exists" in captured.out
        mock_config.add_source.assert_not_called()

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_add_source_invalid_priority(self, mock_config_class, capsys):
        """Test adding source with invalid priority."""
        mock_config = Mock()
        mock_config.get_source.return_value = None  # Source doesn't exist
        mock_config_class.return_value = mock_config

        args = Namespace(
            url="https://github.com/owner/repo",
            branch="main",
            priority=2000,  # Invalid: > 1000
            disabled=False,
        )

        result = handle_add_skill_source(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Priority must be between 0 and 1000" in captured.out

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_add_source_with_priority_conflict(self, mock_config_class, capsys):
        """Test adding source with priority conflict warning."""
        mock_config = Mock()
        mock_config.get_source.return_value = None
        mock_config.validate_priority_conflicts.return_value = {
            "repo": {"priority": 100, "conflicts": ["other-repo"]}
        }
        mock_config_class.return_value = mock_config

        args = Namespace(
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            disabled=False,
            skip_test=True,
            test=False,
        )

        result = handle_add_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Priority conflicts detected" in captured.out

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_add_source_disabled(self, mock_config_class, capsys):
        """Test adding source as disabled."""
        mock_config = Mock()
        mock_config.get_source.return_value = None
        mock_config.validate_priority_conflicts.return_value = {}
        mock_config_class.return_value = mock_config

        args = Namespace(
            url="https://github.com/owner/repo",
            branch="develop",
            priority=50,
            disabled=True,  # Add as disabled
            skip_test=True,
            test=False,
        )

        result = handle_add_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Added skill source: repo" in captured.out
        assert "disabled" in captured.out
        # Check the source was created with enabled=False
        call_args = mock_config.add_source.call_args[0][0]
        assert call_args.enabled is False


class TestHandleListSkillSources:
    """Test list skill sources command."""

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_list_empty(self, mock_config_class, capsys):
        """Test listing when no sources configured."""
        mock_config = Mock()
        mock_config.load.return_value = []
        mock_config_class.return_value = mock_config

        args = Namespace(by_priority=False, enabled_only=False, json=False)

        result = handle_list_skill_sources(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No skill sources configured" in captured.out

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_list_with_sources(self, mock_config_class, capsys):
        """Test listing sources."""
        mock_config = Mock()
        sources = [
            SkillSource(
                id="repo1",
                type="git",
                url="https://github.com/owner/repo1",
                branch="main",
                priority=100,
                enabled=True,
            ),
            SkillSource(
                id="repo2",
                type="git",
                url="https://github.com/owner/repo2",
                branch="develop",
                priority=50,
                enabled=False,
            ),
        ]
        mock_config.load.return_value = sources
        mock_config_class.return_value = mock_config

        args = Namespace(by_priority=False, enabled_only=False, json=False)

        result = handle_list_skill_sources(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "repo1" in captured.out
        assert "repo2" in captured.out
        assert "Enabled" in captured.out
        assert "Disabled" in captured.out

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_list_enabled_only(self, mock_config_class, capsys):
        """Test listing only enabled sources."""
        mock_config = Mock()
        sources = [
            SkillSource(
                id="repo1",
                type="git",
                url="https://github.com/owner/repo1",
                branch="main",
                priority=100,
                enabled=True,
            ),
            SkillSource(
                id="repo2",
                type="git",
                url="https://github.com/owner/repo2",
                branch="main",
                priority=50,
                enabled=False,
            ),
        ]
        mock_config.load.return_value = sources
        mock_config_class.return_value = mock_config

        args = Namespace(by_priority=False, enabled_only=True, json=False)

        result = handle_list_skill_sources(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "repo1" in captured.out
        assert "repo2" not in captured.out

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_list_json_output(self, mock_config_class, capsys):
        """Test JSON output format."""
        mock_config = Mock()
        sources = [
            SkillSource(
                id="repo1",
                type="git",
                url="https://github.com/owner/repo1",
                branch="main",
                priority=100,
                enabled=True,
            ),
        ]
        mock_config.load.return_value = sources
        mock_config_class.return_value = mock_config

        args = Namespace(by_priority=False, enabled_only=False, json=True)

        result = handle_list_skill_sources(args)

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output) == 1
        assert output[0]["id"] == "repo1"
        assert output[0]["enabled"] is True

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_list_by_priority(self, mock_config_class, capsys):
        """Test sorting by priority."""
        mock_config = Mock()
        sources = [
            SkillSource(
                id="low-priority",
                type="git",
                url="https://github.com/owner/repo1",
                branch="main",
                priority=200,
                enabled=True,
            ),
            SkillSource(
                id="high-priority",
                type="git",
                url="https://github.com/owner/repo2",
                branch="main",
                priority=50,
                enabled=True,
            ),
        ]
        mock_config.load.return_value = sources
        mock_config_class.return_value = mock_config

        args = Namespace(by_priority=True, enabled_only=False, json=False)

        result = handle_list_skill_sources(args)

        assert result == 0
        captured = capsys.readouterr()
        # Check that high-priority appears before low-priority
        high_pos = captured.out.find("high-priority")
        low_pos = captured.out.find("low-priority")
        assert high_pos < low_pos


class TestHandleRemoveSkillSource:
    """Test remove skill source command."""

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    @patch("builtins.input")
    def test_remove_source_with_confirmation(
        self, mock_input, mock_config_class, capsys
    ):
        """Test removing source with user confirmation."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config
        mock_input.return_value = "y"

        args = Namespace(source_id="repo", force=False)

        result = handle_remove_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Removed skill source: repo" in captured.out
        mock_config.remove_source.assert_called_once_with("repo")

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    @patch("builtins.input")
    def test_remove_source_cancelled(self, mock_input, mock_config_class, capsys):
        """Test cancelling removal."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config
        mock_input.return_value = "n"

        args = Namespace(source_id="repo", force=False)

        result = handle_remove_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Cancelled" in captured.out
        mock_config.remove_source.assert_not_called()

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_remove_source_force(self, mock_config_class, capsys):
        """Test removing source with --force flag."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config

        args = Namespace(source_id="repo", force=True)

        result = handle_remove_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Removed skill source: repo" in captured.out
        mock_config.remove_source.assert_called_once_with("repo")

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_remove_source_not_found(self, mock_config_class, capsys):
        """Test removing non-existent source."""
        mock_config = Mock()
        mock_config.get_source.return_value = None
        mock_config_class.return_value = mock_config

        args = Namespace(source_id="nonexistent", force=True)

        result = handle_remove_skill_source(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Source not found" in captured.out


class TestHandleUpdateSkillSources:
    """Test update skill sources command."""

    @patch("claude_mpm.cli.commands.skill_source.GitSkillSourceManager")
    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_update_specific_source_success(
        self, mock_config_class, mock_manager_class, capsys
    ):
        """Test updating a specific source successfully."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config

        mock_manager = Mock()
        mock_manager.sync_source.return_value = {
            "synced": True,
            "skills_discovered": 5,
            "files_updated": 2,
        }
        mock_manager_class.return_value = mock_manager

        args = Namespace(source_id="repo", force=False)

        result = handle_update_skill_sources(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Successfully updated repo" in captured.out
        assert "Skills discovered: 5" in captured.out

    @patch("claude_mpm.cli.commands.skill_source.GitSkillSourceManager")
    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_update_specific_source_not_found(
        self, mock_config_class, mock_manager_class, capsys
    ):
        """Test updating non-existent source."""
        mock_config = Mock()
        mock_config.get_source.return_value = None
        mock_config_class.return_value = mock_config

        args = Namespace(source_id="nonexistent", force=False)

        result = handle_update_skill_sources(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Source not found" in captured.out

    @patch("claude_mpm.cli.commands.skill_source.GitSkillSourceManager")
    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_update_specific_source_failure(
        self, mock_config_class, mock_manager_class, capsys
    ):
        """Test update failure."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config

        mock_manager = Mock()
        mock_manager.sync_source.return_value = {
            "success": False,
            "error": "Git fetch failed",
        }
        mock_manager_class.return_value = mock_manager

        args = Namespace(source_id="repo", force=False)

        result = handle_update_skill_sources(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Failed to update repo" in captured.out
        assert "Git fetch failed" in captured.out

    @patch("claude_mpm.cli.commands.skill_source.GitSkillSourceManager")
    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_update_all_sources(self, mock_config_class, mock_manager_class, capsys):
        """Test updating all sources."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_manager = Mock()
        mock_manager.sync_all_sources.return_value = {
            "synced_count": 2,
            "failed_count": 1,
            "sources": {
                "repo1": {"synced": True, "skills_discovered": 3},
                "repo2": {"synced": True, "skills_discovered": 7},
                "repo3": {"synced": False, "error": "Network error"},
            },
        }
        mock_manager_class.return_value = mock_manager

        args = Namespace(source_id=None, force=False)

        result = handle_update_skill_sources(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Updated 2/3 sources" in captured.out
        assert "repo1: 3 skills" in captured.out
        assert "repo2: 7 skills" in captured.out
        assert "repo3: Network error" in captured.out


class TestHandleEnableSkillSource:
    """Test enable skill source command."""

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_enable_source_success(self, mock_config_class, capsys):
        """Test enabling a disabled source."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=False,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config

        args = Namespace(source_id="repo")

        result = handle_enable_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Enabled skill source: repo" in captured.out
        assert source.enabled is True
        mock_config.update_source.assert_called_once()

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_enable_source_already_enabled(self, mock_config_class, capsys):
        """Test enabling an already enabled source."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config

        args = Namespace(source_id="repo")

        result = handle_enable_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "already enabled" in captured.out

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_enable_source_not_found(self, mock_config_class, capsys):
        """Test enabling non-existent source."""
        mock_config = Mock()
        mock_config.get_source.return_value = None
        mock_config_class.return_value = mock_config

        args = Namespace(source_id="nonexistent")

        result = handle_enable_skill_source(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Source not found" in captured.out


class TestHandleDisableSkillSource:
    """Test disable skill source command."""

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_disable_source_success(self, mock_config_class, capsys):
        """Test disabling an enabled source."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config

        args = Namespace(source_id="repo")

        result = handle_disable_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Disabled skill source: repo" in captured.out
        assert source.enabled is False
        mock_config.update_source.assert_called_once()

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_disable_source_already_disabled(self, mock_config_class, capsys):
        """Test disabling an already disabled source."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=False,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config

        args = Namespace(source_id="repo")

        result = handle_disable_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "already disabled" in captured.out


class TestHandleShowSkillSource:
    """Test show skill source command."""

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_show_source_basic(self, mock_config_class, capsys):
        """Test showing source details without skills."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config

        args = Namespace(source_id="repo", skills=False)

        result = handle_show_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Skill Source: repo" in captured.out
        assert "https://github.com/owner/repo" in captured.out
        assert "Branch: main" in captured.out
        assert "Priority: 100" in captured.out

    @patch("claude_mpm.cli.commands.skill_source.SkillDiscoveryService")
    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_show_source_with_skills(
        self, mock_config_class, mock_discovery_class, capsys
    ):
        """Test showing source with skills list."""
        mock_config = Mock()
        source = SkillSource(
            id="repo",
            type="git",
            url="https://github.com/owner/repo",
            branch="main",
            priority=100,
            enabled=True,
        )
        mock_config.get_source.return_value = source
        mock_config_class.return_value = mock_config

        mock_discovery = Mock()
        mock_discovery.discover_skills.return_value = [
            {
                "name": "skill1",
                "description": "Test skill 1",
                "source_id": "repo",
            },
            {
                "name": "skill2",
                "description": "Test skill 2",
                "source_id": "repo",
            },
            {
                "name": "skill3",
                "description": "Other source skill",
                "source_id": "other",
            },
        ]
        mock_discovery_class.return_value = mock_discovery

        args = Namespace(source_id="repo", skills=True)

        result = handle_show_skill_source(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Skills (2)" in captured.out
        assert "skill1" in captured.out
        assert "skill2" in captured.out
        assert "skill3" not in captured.out  # Different source

    @patch("claude_mpm.cli.commands.skill_source.SkillSourceConfiguration")
    def test_show_source_not_found(self, mock_config_class, capsys):
        """Test showing non-existent source."""
        mock_config = Mock()
        mock_config.get_source.return_value = None
        mock_config_class.return_value = mock_config

        args = Namespace(source_id="nonexistent", skills=False)

        result = handle_show_skill_source(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Source not found" in captured.out
