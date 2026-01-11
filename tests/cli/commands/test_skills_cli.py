"""
Comprehensive tests for the SkillsManagementCommand class.

WHY: The skills command manages Claude Code skills across multiple deployment modes,
including bundled skills, Git sources, and GitHub deployment. This is critical functionality
that needs comprehensive test coverage.

DESIGN DECISIONS:
- Test all subcommands (list, deploy, validate, update, info, etc.)
- Mock services to avoid actual file/network operations
- Test error handling and validation
- Verify output formatting and user feedback
- Test both simple and complex workflows
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.cli.commands.skills import SkillsManagementCommand, manage_skills
from claude_mpm.cli.shared.base_command import CommandResult
from claude_mpm.constants import SkillsCommands


class TestSkillsManagementCommand:
    """Test SkillsManagementCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = SkillsManagementCommand()

    def test_initialization(self):
        """Test SkillsManagementCommand initialization."""
        assert self.command.command_name == "skills"
        assert self.command.logger is not None
        assert self.command._skills_service is None  # Lazy loaded
        assert self.command._skills_deployer is None  # Lazy loaded

    def test_skills_service_lazy_loading(self):
        """Test skills service is lazily loaded."""
        assert self.command._skills_service is None

        with patch("claude_mpm.cli.commands.skills.SkillsService") as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance

            # Access property triggers lazy loading
            service = self.command.skills_service

            assert service == mock_instance
            assert self.command._skills_service == mock_instance
            mock_service.assert_called_once()

    def test_skills_deployer_lazy_loading(self):
        """Test skills deployer is lazily loaded."""
        assert self.command._skills_deployer is None

        with patch(
            "claude_mpm.cli.commands.skills.SkillsDeployerService"
        ) as mock_deployer:
            mock_instance = Mock()
            mock_deployer.return_value = mock_instance

            # Access property triggers lazy loading
            deployer = self.command.skills_deployer

            assert deployer == mock_instance
            assert self.command._skills_deployer == mock_instance
            mock_deployer.assert_called_once()

    def test_validate_args_success(self):
        """Test argument validation with valid args."""
        args = Namespace()
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_validate_command_requires_skill_name(self):
        """Test validate command requires skill name."""
        args = Namespace(skills_command=SkillsCommands.VALIDATE.value, skill_name=None)
        error = self.command.validate_args(args)
        assert error == "Validate command requires a skill name"

    def test_validate_args_info_command_requires_skill_name(self):
        """Test info command requires skill name."""
        args = Namespace(skills_command=SkillsCommands.INFO.value, skill_name=None)
        error = self.command.validate_args(args)
        assert error == "Info command requires a skill name"

    def test_run_default_behavior_calls_list(self):
        """Test default behavior (no subcommand) calls list."""
        args = Namespace()

        with patch.object(self.command, "_list_skills") as mock_list:
            mock_list.return_value = CommandResult(success=True, exit_code=0)

            result = self.command.run(args)

            assert result.success is True
            mock_list.assert_called_once_with(args)

    def test_run_routes_to_list(self):
        """Test routing to list command."""
        args = Namespace(skills_command=SkillsCommands.LIST.value)

        with patch.object(self.command, "_list_skills") as mock_list:
            mock_list.return_value = CommandResult(success=True, exit_code=0)

            result = self.command.run(args)

            assert result.success is True
            mock_list.assert_called_once_with(args)

    def test_run_routes_to_deploy(self):
        """Test routing to deploy command."""
        args = Namespace(skills_command=SkillsCommands.DEPLOY.value)

        with patch.object(self.command, "_deploy_skills") as mock_deploy:
            mock_deploy.return_value = CommandResult(success=True, exit_code=0)

            result = self.command.run(args)

            assert result.success is True
            mock_deploy.assert_called_once_with(args)

    def test_run_routes_to_validate(self):
        """Test routing to validate command."""
        args = Namespace(skills_command=SkillsCommands.VALIDATE.value)

        with patch.object(self.command, "_validate_skill") as mock_validate:
            mock_validate.return_value = CommandResult(success=True, exit_code=0)

            result = self.command.run(args)

            assert result.success is True
            mock_validate.assert_called_once_with(args)

    def test_run_routes_to_update(self):
        """Test routing to update command."""
        args = Namespace(skills_command=SkillsCommands.UPDATE.value)

        with patch.object(self.command, "_update_skills") as mock_update:
            mock_update.return_value = CommandResult(success=True, exit_code=0)

            result = self.command.run(args)

            assert result.success is True
            mock_update.assert_called_once_with(args)

    def test_run_routes_to_info(self):
        """Test routing to info command."""
        args = Namespace(skills_command=SkillsCommands.INFO.value)

        with patch.object(self.command, "_show_skill_info") as mock_info:
            mock_info.return_value = CommandResult(success=True, exit_code=0)

            result = self.command.run(args)

            assert result.success is True
            mock_info.assert_called_once_with(args)

    def test_run_routes_to_remove(self):
        """Test routing to remove command."""
        args = Namespace(skills_command=SkillsCommands.REMOVE.value)

        with patch.object(self.command, "_remove_skills") as mock_remove:
            mock_remove.return_value = CommandResult(success=True, exit_code=0)

            result = self.command.run(args)

            assert result.success is True
            mock_remove.assert_called_once_with(args)

    def test_run_unknown_command(self):
        """Test handling of unknown subcommand."""
        args = Namespace(skills_command="unknown_command")

        result = self.command.run(args)

        assert result.success is False
        assert result.exit_code == 1
        assert "Unknown skills command" in result.message

    def test_run_handles_exceptions(self):
        """Test exception handling in run method."""
        args = Namespace(skills_command=SkillsCommands.LIST.value)

        with patch.object(self.command, "_list_skills") as mock_list:
            mock_list.side_effect = Exception("Test error")

            result = self.command.run(args)

            assert result.success is False
            assert result.exit_code == 1
            assert "Skills command failed" in result.message


class TestListSkills:
    """Test _list_skills command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = SkillsManagementCommand()

    @patch("claude_mpm.cli.commands.skills.console")
    def test_list_skills_all(self, mock_console):
        """Test listing all skills."""
        args = Namespace(verbose=False)

        mock_skills = [
            {
                "name": "skill1",
                "category": "toolchains",
                "metadata": {"description": "Test 1"},
            },
            {
                "name": "skill2",
                "category": "universal",
                "metadata": {"description": "Test 2"},
            },
        ]

        with patch.object(
            self.command.skills_service, "discover_bundled_skills"
        ) as mock_discover:
            mock_discover.return_value = mock_skills

            result = self.command._list_skills(args)

            assert result.success is True
            assert result.exit_code == 0
            mock_discover.assert_called_once()

    @patch("claude_mpm.cli.commands.skills.console")
    def test_list_skills_by_agent(self, mock_console):
        """Test listing skills for specific agent."""
        args = Namespace(agent="test-agent", verbose=False)

        mock_skills = ["skill1", "skill2"]

        with patch.object(
            self.command.skills_service, "get_skills_for_agent"
        ) as mock_get_skills:
            mock_get_skills.return_value = mock_skills
            with patch.object(self.command, "_get_skill_metadata") as mock_metadata:
                mock_metadata.return_value = {"description": "Test skill"}

                result = self.command._list_skills(args)

                assert result.success is True
                mock_get_skills.assert_called_once_with("test-agent")

    @patch("claude_mpm.cli.commands.skills.console")
    def test_list_skills_by_category(self, mock_console):
        """Test filtering skills by category."""
        args = Namespace(category="toolchains", verbose=False)

        mock_skills = [
            {"name": "skill1", "category": "toolchains", "metadata": {}},
            {"name": "skill2", "category": "universal", "metadata": {}},
        ]

        with patch.object(
            self.command.skills_service, "discover_bundled_skills"
        ) as mock_discover:
            mock_discover.return_value = mock_skills

            result = self.command._list_skills(args)

            assert result.success is True
            # Should filter to only toolchains category
            mock_discover.assert_called_once()

    @patch("claude_mpm.cli.commands.skills.console")
    def test_list_skills_empty_result(self, mock_console):
        """Test behavior when no skills match filter."""
        args = Namespace(category="nonexistent", verbose=False)

        with patch.object(
            self.command.skills_service, "discover_bundled_skills"
        ) as mock_discover:
            mock_discover.return_value = []

            result = self.command._list_skills(args)

            assert result.success is True
            assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_list_skills_verbose(self, mock_console):
        """Test verbose output shows descriptions."""
        args = Namespace(verbose=True)

        mock_skills = [
            {
                "name": "skill1",
                "category": "toolchains",
                "metadata": {"description": "Test description", "version": "1.0.0"},
            },
        ]

        with patch.object(
            self.command.skills_service, "discover_bundled_skills"
        ) as mock_discover:
            mock_discover.return_value = mock_skills

            result = self.command._list_skills(args)

            assert result.success is True

    @patch("claude_mpm.cli.commands.skills.console")
    def test_list_skills_handles_errors(self, mock_console):
        """Test error handling in list command."""
        args = Namespace(verbose=False)

        with patch.object(
            self.command.skills_service, "discover_bundled_skills"
        ) as mock_discover:
            mock_discover.side_effect = Exception("Discovery failed")

            result = self.command._list_skills(args)

            assert result.success is False
            assert result.exit_code == 1


class TestDeploySkills:
    """Test _deploy_skills command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = SkillsManagementCommand()

    @patch("claude_mpm.cli.commands.skills.console")
    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_deploy_skills_success(
        self, mock_config_class, mock_manager_class, mock_console
    ):
        """Test successful skill deployment."""
        args = Namespace(force=False, skills=None)

        # Mock config
        mock_config = Mock()
        mock_config_class.load.return_value = mock_config

        # Mock manager
        mock_manager = Mock()
        mock_manager.sync_all_sources.return_value = {"source1": {"synced": True}}
        mock_manager.deploy_skills_to_project.return_value = {
            "deployed": ["skill1", "skill2"],
            "updated": [],
            "skipped": [],
            "failed": [],
            "deployment_dir": "/test/dir",
        }
        mock_manager_class.return_value = mock_manager

        result = self.command._deploy_skills(args)

        assert result.success is True
        assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_deploy_skills_with_failures(
        self, mock_config_class, mock_manager_class, mock_console
    ):
        """Test deployment with some failures."""
        args = Namespace(force=False, skills=None)

        mock_config = Mock()
        mock_config_class.load.return_value = mock_config

        mock_manager = Mock()
        mock_manager.sync_all_sources.return_value = {}
        mock_manager.deploy_skills_to_project.return_value = {
            "deployed": ["skill1"],
            "updated": [],
            "skipped": [],
            "failed": ["skill2"],
            "deployment_dir": "/test/dir",
        }
        mock_manager_class.return_value = mock_manager

        result = self.command._deploy_skills(args)

        assert result.success is False
        assert result.exit_code == 1

    @patch("claude_mpm.cli.commands.skills.console")
    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_deploy_skills_force(
        self, mock_config_class, mock_manager_class, mock_console
    ):
        """Test force deployment."""
        args = Namespace(force=True, skills=None)

        mock_config = Mock()
        mock_config_class.load.return_value = mock_config

        mock_manager = Mock()
        mock_manager.sync_all_sources.return_value = {}
        mock_manager.deploy_skills_to_project.return_value = {
            "deployed": [],
            "updated": ["skill1"],
            "skipped": [],
            "failed": [],
            "deployment_dir": "/test/dir",
        }
        mock_manager_class.return_value = mock_manager

        result = self.command._deploy_skills(args)

        assert result.success is True
        mock_manager.deploy_skills_to_project.assert_called_once()
        call_kwargs = mock_manager.deploy_skills_to_project.call_args[1]
        assert call_kwargs["force"] is True

    @patch("claude_mpm.cli.commands.skills.console")
    @patch("claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_deploy_specific_skills(
        self, mock_config_class, mock_manager_class, mock_console
    ):
        """Test deploying specific skills."""
        args = Namespace(force=False, skills=["skill1", "skill2"])

        mock_config = Mock()
        mock_config_class.load.return_value = mock_config

        mock_manager = Mock()
        mock_manager.sync_all_sources.return_value = {}
        mock_manager.deploy_skills_to_project.return_value = {
            "deployed": ["skill1", "skill2"],
            "updated": [],
            "skipped": [],
            "failed": [],
            "deployment_dir": "/test/dir",
        }
        mock_manager_class.return_value = mock_manager

        result = self.command._deploy_skills(args)

        assert result.success is True
        call_kwargs = mock_manager.deploy_skills_to_project.call_args[1]
        assert call_kwargs["skill_list"] == ["skill1", "skill2"]

    @patch("claude_mpm.cli.commands.skills.console")
    @patch("claude_mpm.config.skill_sources.SkillSourceConfiguration")
    def test_deploy_skills_handles_errors(self, mock_config_class, mock_console):
        """Test error handling in deploy command."""
        args = Namespace(force=False, skills=None)

        mock_config_class.load.side_effect = Exception("Config error")

        result = self.command._deploy_skills(args)

        assert result.success is False
        assert result.exit_code == 1


class TestValidateSkill:
    """Test _validate_skill command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = SkillsManagementCommand()

    @patch("claude_mpm.cli.commands.skills.console")
    def test_validate_valid_skill(self, mock_console):
        """Test validation of a valid skill."""
        args = Namespace(skill_name="test-skill", strict=False)

        with patch.object(
            self.command.skills_service, "validate_skill"
        ) as mock_validate:
            mock_validate.return_value = {"valid": True, "warnings": [], "errors": []}

            result = self.command._validate_skill(args)

            assert result.success is True
            assert result.exit_code == 0
            mock_validate.assert_called_once_with("test-skill")

    @patch("claude_mpm.cli.commands.skills.console")
    def test_validate_skill_with_warnings(self, mock_console):
        """Test validation with warnings in normal mode."""
        args = Namespace(skill_name="test-skill", strict=False)

        with patch.object(
            self.command.skills_service, "validate_skill"
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "warnings": ["Missing description"],
                "errors": [],
            }

            result = self.command._validate_skill(args)

            assert result.success is True
            assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_validate_skill_with_warnings_strict_mode(self, mock_console):
        """Test validation with warnings in strict mode."""
        args = Namespace(skill_name="test-skill", strict=True)

        with patch.object(
            self.command.skills_service, "validate_skill"
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "warnings": ["Missing description"],
                "errors": [],
            }

            result = self.command._validate_skill(args)

            # Strict mode treats warnings as errors
            assert result.success is False
            assert result.exit_code == 1

    @patch("claude_mpm.cli.commands.skills.console")
    def test_validate_invalid_skill(self, mock_console):
        """Test validation of invalid skill."""
        args = Namespace(skill_name="test-skill", strict=False)

        with patch.object(
            self.command.skills_service, "validate_skill"
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "warnings": [],
                "errors": ["Invalid frontmatter", "Missing required field"],
            }

            result = self.command._validate_skill(args)

            assert result.success is False
            assert result.exit_code == 1

    @patch("claude_mpm.cli.commands.skills.console")
    def test_validate_skill_handles_errors(self, mock_console):
        """Test error handling in validate command."""
        args = Namespace(skill_name="test-skill", strict=False)

        with patch.object(
            self.command.skills_service, "validate_skill"
        ) as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            result = self.command._validate_skill(args)

            assert result.success is False
            assert result.exit_code == 1


class TestUpdateSkills:
    """Test _update_skills command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = SkillsManagementCommand()

    @patch("claude_mpm.cli.commands.skills.console")
    def test_update_no_updates_available(self, mock_console):
        """Test update when all skills are current."""
        args = Namespace(skill_names=[], check_only=False, force=False)

        with patch.object(
            self.command.skills_service, "check_for_updates"
        ) as mock_check:
            mock_check.return_value = {"updates_available": []}

            result = self.command._update_skills(args)

            assert result.success is True
            assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_update_check_only(self, mock_console):
        """Test check-only mode."""
        args = Namespace(skill_names=[], check_only=True, force=False)

        with patch.object(
            self.command.skills_service, "check_for_updates"
        ) as mock_check:
            mock_check.return_value = {
                "updates_available": [
                    {
                        "skill": "skill1",
                        "current_version": "1.0.0",
                        "latest_version": "1.1.0",
                    }
                ]
            }

            result = self.command._update_skills(args)

            assert result.success is True
            assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_update_install_updates(self, mock_console):
        """Test installing available updates."""
        args = Namespace(skill_names=[], check_only=False, force=False)

        updates = [
            {"skill": "skill1", "current_version": "1.0.0", "latest_version": "1.1.0"}
        ]

        with patch.object(
            self.command.skills_service, "check_for_updates"
        ) as mock_check:
            mock_check.return_value = {"updates_available": updates}

            with patch.object(
                self.command.skills_service, "install_updates"
            ) as mock_install:
                mock_install.return_value = {"updated": ["skill1"], "errors": {}}

                result = self.command._update_skills(args)

                assert result.success is True
                assert result.exit_code == 0
                mock_install.assert_called_once()

    @patch("claude_mpm.cli.commands.skills.console")
    def test_update_with_errors(self, mock_console):
        """Test update with installation errors."""
        args = Namespace(skill_names=[], check_only=False, force=False)

        updates = [
            {"skill": "skill1", "current_version": "1.0.0", "latest_version": "1.1.0"}
        ]

        with patch.object(
            self.command.skills_service, "check_for_updates"
        ) as mock_check:
            mock_check.return_value = {"updates_available": updates}

            with patch.object(
                self.command.skills_service, "install_updates"
            ) as mock_install:
                mock_install.return_value = {
                    "updated": [],
                    "errors": {"skill1": "Network error"},
                }

                result = self.command._update_skills(args)

                assert result.success is False
                assert result.exit_code == 1

    @patch("claude_mpm.cli.commands.skills.console")
    def test_update_handles_errors(self, mock_console):
        """Test error handling in update command."""
        args = Namespace(skill_names=[], check_only=False, force=False)

        with patch.object(
            self.command.skills_service, "check_for_updates"
        ) as mock_check:
            mock_check.side_effect = Exception("Update check failed")

            result = self.command._update_skills(args)

            assert result.success is False
            assert result.exit_code == 1


class TestShowSkillInfo:
    """Test _show_skill_info command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = SkillsManagementCommand()

    @patch("claude_mpm.cli.commands.skills.console")
    def test_show_skill_info_basic(self, mock_console):
        """Test showing basic skill info."""
        args = Namespace(skill_name="test-skill", show_content=False)

        with patch.object(self.command, "_get_skill_metadata") as mock_metadata:
            mock_metadata.return_value = {
                "description": "Test skill",
                "category": "toolchains",
                "version": "1.0.0",
                "source": "bundled",
            }

            with patch.object(
                self.command.skills_service, "get_agents_for_skill"
            ) as mock_agents:
                mock_agents.return_value = ["agent1", "agent2"]

                result = self.command._show_skill_info(args)

                assert result.success is True
                assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_show_skill_info_missing_skill(self, mock_console):
        """Test showing info for non-existent skill."""
        args = Namespace(skill_name="nonexistent", show_content=False)

        with patch.object(self.command, "_get_skill_metadata") as mock_metadata:
            mock_metadata.return_value = None

            result = self.command._show_skill_info(args)

            assert result.success is False
            assert result.exit_code == 1

    @patch("claude_mpm.cli.commands.skills.console")
    def test_show_skill_info_with_content(self, mock_console):
        """Test showing skill info with content."""
        args = Namespace(skill_name="test-skill", show_content=True)

        with patch.object(self.command, "_get_skill_metadata") as mock_metadata:
            mock_metadata.return_value = {
                "description": "Test skill",
                "category": "toolchains",
            }

            with patch.object(
                self.command.skills_service, "get_agents_for_skill"
            ) as mock_agents:
                mock_agents.return_value = []

                with patch.object(
                    self.command.skills_service, "get_skill_path"
                ) as mock_path:
                    mock_skill_path = Mock()
                    mock_skill_md = Mock()
                    mock_skill_md.exists.return_value = True
                    mock_skill_md.read_text.return_value = "# Skill content"
                    mock_skill_path.__truediv__ = Mock(return_value=mock_skill_md)
                    mock_path.return_value = mock_skill_path

                    result = self.command._show_skill_info(args)

                    assert result.success is True

    @patch("claude_mpm.cli.commands.skills.console")
    def test_show_skill_info_handles_errors(self, mock_console):
        """Test error handling in info command."""
        args = Namespace(skill_name="test-skill", show_content=False)

        with patch.object(self.command, "_get_skill_metadata") as mock_metadata:
            mock_metadata.side_effect = Exception("Metadata error")

            result = self.command._show_skill_info(args)

            assert result.success is False
            assert result.exit_code == 1


class TestRemoveSkills:
    """Test _remove_skills command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = SkillsManagementCommand()

    @patch("claude_mpm.cli.commands.skills.console")
    def test_remove_specific_skills(self, mock_console):
        """Test removing specific skills."""
        args = Namespace(skill_names=["skill1", "skill2"], all=False)

        with patch.object(self.command.skills_deployer, "remove_skills") as mock_remove:
            mock_remove.return_value = {
                "removed_count": 2,
                "removed_skills": ["skill1", "skill2"],
                "errors": [],
            }

            result = self.command._remove_skills(args)

            assert result.success is True
            assert result.exit_code == 0
            mock_remove.assert_called_once_with(["skill1", "skill2"])

    @patch("claude_mpm.cli.commands.skills.console")
    def test_remove_all_skills(self, mock_console):
        """Test removing all skills."""
        args = Namespace(skill_names=None, all=True)

        with patch.object(self.command.skills_deployer, "remove_skills") as mock_remove:
            mock_remove.return_value = {
                "removed_count": 5,
                "removed_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
                "errors": [],
            }

            result = self.command._remove_skills(args)

            assert result.success is True
            mock_remove.assert_called_once_with(None)

    @patch("claude_mpm.cli.commands.skills.console")
    def test_remove_with_errors(self, mock_console):
        """Test remove with errors."""
        args = Namespace(skill_names=["skill1"], all=False)

        with patch.object(self.command.skills_deployer, "remove_skills") as mock_remove:
            mock_remove.return_value = {
                "removed_count": 0,
                "removed_skills": [],
                "errors": ["skill1: Not found"],
            }

            result = self.command._remove_skills(args)

            assert result.success is False
            assert result.exit_code == 1

    @patch("claude_mpm.cli.commands.skills.console")
    def test_remove_no_args(self, mock_console):
        """Test remove without specifying skills or --all."""
        args = Namespace(skill_names=None, all=False)

        result = self.command._remove_skills(args)

        assert result.success is False
        assert result.exit_code == 1

    @patch("claude_mpm.cli.commands.skills.console")
    def test_remove_handles_errors(self, mock_console):
        """Test error handling in remove command."""
        args = Namespace(skill_names=["skill1"], all=False)

        with patch.object(self.command.skills_deployer, "remove_skills") as mock_remove:
            mock_remove.side_effect = Exception("Remove error")

            result = self.command._remove_skills(args)

            assert result.success is False
            assert result.exit_code == 1


class TestManageSkills:
    """Test manage_skills entry point function."""

    @patch("claude_mpm.cli.commands.skills.console")
    def test_manage_skills_success(self, mock_console):
        """Test successful command execution."""
        args = Namespace(skills_command=SkillsCommands.LIST.value)

        with patch("claude_mpm.cli.commands.skills.SkillsService"):
            result = manage_skills(args)

            assert result == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_manage_skills_validation_error(self, mock_console):
        """Test validation error returns exit code 1."""
        args = Namespace(skills_command=SkillsCommands.VALIDATE.value, skill_name=None)

        result = manage_skills(args)

        assert result == 1

    @patch("claude_mpm.cli.commands.skills.console")
    def test_manage_skills_command_failure(self, mock_console):
        """Test command failure returns non-zero exit code."""
        args = Namespace(skills_command=SkillsCommands.LIST.value)

        with patch("claude_mpm.cli.commands.skills.SkillsService") as mock_service:
            mock_service.return_value.discover_bundled_skills.side_effect = Exception(
                "Error"
            )

            result = manage_skills(args)

            assert result == 1


class TestCollectionManagement:
    """Test collection management commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = SkillsManagementCommand()

    @patch("claude_mpm.cli.commands.skills.console")
    def test_collection_list(self, mock_console):
        """Test listing collections."""
        args = Namespace()

        with patch.object(
            self.command.skills_deployer, "list_collections"
        ) as mock_list:
            mock_list.return_value = {
                "default_collection": "main",
                "enabled_count": 2,
                "total_count": 3,
                "collections": {
                    "main": {
                        "url": "https://github.com/owner/repo1",
                        "priority": 100,
                        "enabled": True,
                        "last_update": "2024-01-01",
                    }
                },
            }

            result = self.command._collection_list(args)

            assert result.success is True
            assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_collection_add(self, mock_console):
        """Test adding a collection."""
        args = Namespace(
            collection_name="test",
            collection_url="https://github.com/owner/repo",
            priority=100,
        )

        with patch.object(self.command.skills_deployer, "add_collection") as mock_add:
            mock_add.return_value = {"message": "Collection added"}

            result = self.command._collection_add(args)

            assert result.success is True
            assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_collection_remove(self, mock_console):
        """Test removing a collection."""
        args = Namespace(collection_name="test")

        with patch.object(
            self.command.skills_deployer, "remove_collection"
        ) as mock_remove:
            mock_remove.return_value = {
                "message": "Collection removed",
                "directory_removed": True,
            }

            result = self.command._collection_remove(args)

            assert result.success is True
            assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_collection_enable(self, mock_console):
        """Test enabling a collection."""
        args = Namespace(collection_name="test")

        with patch.object(
            self.command.skills_deployer, "enable_collection"
        ) as mock_enable:
            mock_enable.return_value = {"message": "Collection enabled"}

            result = self.command._collection_enable(args)

            assert result.success is True
            assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_collection_disable(self, mock_console):
        """Test disabling a collection."""
        args = Namespace(collection_name="test")

        with patch.object(
            self.command.skills_deployer, "disable_collection"
        ) as mock_disable:
            mock_disable.return_value = {"message": "Collection disabled"}

            result = self.command._collection_disable(args)

            assert result.success is True
            assert result.exit_code == 0

    @patch("claude_mpm.cli.commands.skills.console")
    def test_collection_set_default(self, mock_console):
        """Test setting default collection."""
        args = Namespace(collection_name="test")

        with patch.object(
            self.command.skills_deployer, "set_default_collection"
        ) as mock_set:
            mock_set.return_value = {
                "message": "Default collection set",
                "previous_default": "main",
            }

            result = self.command._collection_set_default(args)

            assert result.success is True
            assert result.exit_code == 0
