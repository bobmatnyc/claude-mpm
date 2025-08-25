"""
Comprehensive unit tests for the agents command module.

This module provides extensive test coverage for all agents command functionality
to serve as a safety net during refactoring.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.commands.agents import AgentsCommand, manage_agents
from claude_mpm.cli.shared import CommandResult


class TestAgentsCommand:
    """Test suite for AgentsCommand class."""

    @pytest.fixture
    def mock_deployment_service(self):
        """Create a mock deployment service with all required methods."""
        service = MagicMock()

        # Mock list_available_agents
        service.list_available_agents.return_value = [
            {
                "file": "engineer.json",
                "name": "Engineer",
                "description": "Software engineering specialist",
                "version": "1.0.0",
            },
            {
                "file": "qa.json",
                "name": "QA",
                "description": "Quality assurance specialist",
                "version": "1.0.0",
            },
        ]

        # Mock verify_deployment
        service.verify_deployment.return_value = {
            "agents_found": [
                {
                    "file": "engineer.md",
                    "name": "Engineer",
                    "path": "/project/.claude/agents/engineer.md",
                },
                {
                    "file": "qa.md",
                    "name": "QA",
                    "path": "/project/.claude/agents/qa.md",
                },
            ],
            "warnings": [],
        }

        # Mock list_agents_by_tier
        service.list_agents_by_tier.return_value = {
            "project": ["engineer", "qa"],
            "user": ["documentation"],
            "system": ["base", "pm"],
        }

        # Mock deploy_system_agents
        service.deploy_system_agents.return_value = {
            "deployed_count": 2,
            "deployed": [{"name": "engineer"}, {"name": "qa"}],
            "updated": [],
            "errors": [],
        }

        # Mock deploy_project_agents
        service.deploy_project_agents.return_value = {
            "deployed_count": 1,
            "deployed": [{"name": "custom"}],
            "updated": [],
            "errors": [],
        }

        # Mock clean_deployment
        service.clean_deployment.return_value = {
            "cleaned_count": 3,
            "removed": ["engineer.md", "qa.md", "custom.md"],
        }

        # Mock get_agent_details
        service.get_agent_details.return_value = {
            "name": "Engineer",
            "version": "1.0.0",
            "description": "Software engineering specialist",
            "path": "/project/.claude/agents/engineer.md",
        }

        # Mock fix_deployment
        service.fix_deployment.return_value = {
            "fixes_applied": [
                "Fixed frontmatter formatting",
                "Corrected version field",
            ],
        }

        # Mock dependency methods
        service.check_dependencies.return_value = {
            "missing_dependencies": ["numpy", "pandas"],
        }

        service.install_dependencies.return_value = {
            "installed_count": 2,
            "installed": ["numpy", "pandas"],
        }

        service.list_dependencies.return_value = {
            "dependencies": [
                {"name": "numpy", "installed": True},
                {"name": "pandas", "installed": True},
                {"name": "scipy", "installed": False},
            ],
        }

        service.fix_dependencies.return_value = {
            "fixes_applied": ["Installed numpy", "Installed pandas"],
        }

        return service

    @pytest.fixture
    def command(self, mock_deployment_service):
        """Create an AgentsCommand instance with mocked deployment service."""
        cmd = AgentsCommand()
        cmd._deployment_service = mock_deployment_service
        return cmd

    @pytest.fixture
    def mock_args(self):
        """Create mock arguments object."""
        args = MagicMock()
        args.format = "text"
        args.agents_command = None
        return args


class TestListingOperations(TestAgentsCommand):
    """Test listing operations for agents."""

    def test_list_system_agents_text_format(self, command, mock_args):
        """Test listing system agents in text format."""
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.deployed = False
        mock_args.by_tier = False

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert result.exit_code == 0
        assert "Listed 2 agent templates" in result.message
        mock_print.assert_any_call("Available Agent Templates:")
        mock_print.assert_any_call("📄 engineer.json")
        mock_print.assert_any_call("   Name: Engineer")

    def test_list_system_agents_json_format(self, command, mock_args):
        """Test listing system agents in JSON format."""
        mock_args.agents_command = "list"
        mock_args.format = "json"
        mock_args.system = True
        mock_args.deployed = False
        mock_args.by_tier = False

        result = command.run(mock_args)

        assert result.success
        assert result.data["count"] == 2
        assert len(result.data["agents"]) == 2
        assert result.data["agents"][0]["name"] == "Engineer"

    def test_list_deployed_agents_text_format(self, command, mock_args):
        """Test listing deployed agents in text format."""
        mock_args.agents_command = "list"
        mock_args.deployed = True
        mock_args.system = False
        mock_args.by_tier = False

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Listed 2 deployed agents" in result.message
        mock_print.assert_any_call("Deployed Agents:")
        mock_print.assert_any_call("📄 engineer.md")

    def test_list_deployed_agents_with_warnings(
        self, command, mock_args, mock_deployment_service
    ):
        """Test listing deployed agents with warnings."""
        mock_deployment_service.verify_deployment.return_value = {
            "agents_found": [{"file": "test.md", "name": "Test"}],
            "warnings": ["Missing version field", "Invalid frontmatter"],
        }

        mock_args.agents_command = "list"
        mock_args.deployed = True
        mock_args.system = False
        mock_args.by_tier = False

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        mock_print.assert_any_call("\nWarnings:")
        mock_print.assert_any_call("  ⚠️  Missing version field")

    def test_list_agents_by_tier_text_format(self, command, mock_args):
        """Test listing agents grouped by tier in text format."""
        mock_args.agents_command = "list"
        mock_args.by_tier = True

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Agents listed by tier" in result.message
        mock_print.assert_any_call("Agents by Tier/Precedence:")
        mock_print.assert_any_call("\nPROJECT:")
        mock_print.assert_any_call("  • engineer")

    def test_list_agents_by_tier_json_format(self, command, mock_args):
        """Test listing agents by tier in JSON format."""
        mock_args.agents_command = "list"
        mock_args.by_tier = True
        mock_args.format = "json"

        result = command.run(mock_args)

        assert result.success
        assert result.data["project"] == ["engineer", "qa"]
        assert result.data["user"] == ["documentation"]
        assert result.data["system"] == ["base", "pm"]

    def test_list_no_option_specified(self, command, mock_args):
        """Test list command with no specific option."""
        mock_args.agents_command = "list"
        mock_args.system = False
        mock_args.deployed = False
        mock_args.by_tier = False

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert not result.success
        assert result.exit_code == 1
        assert "No list option specified" in result.message


class TestDeploymentOperations(TestAgentsCommand):
    """Test deployment operations for agents."""

    def test_deploy_agents_success(self, command, mock_args):
        """Test successful agent deployment."""
        mock_args.agents_command = "deploy"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Deployed 3 agents" in result.message
        mock_print.assert_any_call("✓ Deployed 2 system agents")
        mock_print.assert_any_call("✓ Deployed 1 project agents")

    def test_deploy_agents_force(self, command, mock_args, mock_deployment_service):
        """Test force deployment of agents."""
        mock_args.agents_command = "force-deploy"

        mock_deployment_service.deploy_system_agents.assert_not_called()

        result = command.run(mock_args)

        assert result.success
        mock_deployment_service.deploy_system_agents.assert_called_once_with(force=True)
        mock_deployment_service.deploy_project_agents.assert_called_once_with(
            force=True
        )

    def test_deploy_agents_no_changes(
        self, command, mock_args, mock_deployment_service
    ):
        """Test deployment when all agents are up to date."""
        mock_deployment_service.deploy_system_agents.return_value = {
            "deployed_count": 0,
            "deployed": [],
        }
        mock_deployment_service.deploy_project_agents.return_value = {
            "deployed_count": 0,
            "deployed": [],
        }

        mock_args.agents_command = "deploy"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        mock_print.assert_any_call("No agents were deployed (all up to date)")

    def test_deploy_agents_json_format(self, command, mock_args):
        """Test deployment with JSON output format."""
        mock_args.agents_command = "deploy"
        mock_args.format = "json"

        result = command.run(mock_args)

        assert result.success
        assert result.data["total_deployed"] == 3
        assert result.data["system_agents"]["deployed_count"] == 2
        assert result.data["project_agents"]["deployed_count"] == 1

    def test_deploy_agents_with_errors(
        self, command, mock_args, mock_deployment_service
    ):
        """Test deployment with errors."""
        mock_deployment_service.deploy_system_agents.side_effect = Exception(
            "Deploy failed"
        )

        mock_args.agents_command = "deploy"

        result = command.run(mock_args)

        assert not result.success
        assert "Error deploying agents" in result.message


class TestCleanupOperations(TestAgentsCommand):
    """Test cleanup operations for agents."""

    def test_clean_agents_success(self, command, mock_args):
        """Test successful agent cleanup."""
        mock_args.agents_command = "clean"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Cleaned 3 agents" in result.message
        mock_print.assert_any_call("✓ Cleaned 3 deployed agents")

    def test_clean_agents_none_to_clean(
        self, command, mock_args, mock_deployment_service
    ):
        """Test cleanup when no agents are deployed."""
        mock_deployment_service.clean_deployment.return_value = {
            "cleaned_count": 0,
            "removed": [],
        }

        mock_args.agents_command = "clean"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        mock_print.assert_any_call("No deployed agents to clean")

    def test_clean_agents_json_format(self, command, mock_args):
        """Test cleanup with JSON output."""
        mock_args.agents_command = "clean"
        mock_args.format = "json"

        result = command.run(mock_args)

        assert result.success
        assert result.data["cleaned_count"] == 3
        assert len(result.data["removed"]) == 3

    def test_cleanup_orphaned_agents_dry_run(self, command, mock_args):
        """Test cleanup orphaned agents in dry-run mode."""
        mock_args.agents_command = "cleanup-orphaned"
        mock_args.dry_run = True
        mock_args.force = False
        mock_args.quiet = False

        with patch(
            "claude_mpm.services.agents.deployment.multi_source_deployment_service.MultiSourceAgentDeploymentService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.cleanup_orphaned_agents.return_value = {
                "orphaned": [
                    {"name": "old-agent", "version": "0.1.0"},
                    {"name": "unused-agent", "version": "0.2.0"},
                ],
                "removed": [],
                "errors": [],
            }

            with patch("builtins.print") as mock_print:
                result = command.run(mock_args)

            assert result.success
            mock_print.assert_any_call("\nFound 2 orphaned agent(s):")
            mock_print.assert_any_call("  - old-agent v0.1.0")
            mock_service.cleanup_orphaned_agents.assert_called_once()
            call_args = mock_service.cleanup_orphaned_agents.call_args
            assert call_args.kwargs["dry_run"] is True

    def test_cleanup_orphaned_agents_force(self, command, mock_args):
        """Test cleanup orphaned agents with force flag."""
        mock_args.agents_command = "cleanup-orphaned"
        mock_args.force = True
        mock_args.dry_run = False
        mock_args.quiet = False

        with patch(
            "claude_mpm.services.agents.deployment.multi_source_deployment_service.MultiSourceAgentDeploymentService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.cleanup_orphaned_agents.return_value = {
                "orphaned": [{"name": "old-agent", "version": "0.1.0"}],
                "removed": [{"name": "old-agent", "version": "0.1.0"}],
                "errors": [],
            }

            with patch("builtins.print") as mock_print:
                result = command.run(mock_args)

            assert result.success
            mock_print.assert_any_call("\n✅ Successfully removed 1 orphaned agent(s)")
            call_args = mock_service.cleanup_orphaned_agents.call_args
            assert call_args.kwargs["dry_run"] is False


class TestViewingOperations(TestAgentsCommand):
    """Test viewing operations for agents."""

    def test_view_agent_success(self, command, mock_args):
        """Test viewing agent details."""
        mock_args.agents_command = "view"
        mock_args.agent_name = "engineer"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Displayed details for engineer" in result.message
        mock_print.assert_any_call("Agent: engineer")
        mock_print.assert_any_call("name: Engineer")

    def test_view_agent_missing_name(self, command, mock_args):
        """Test view command without agent name."""
        mock_args.agents_command = "view"
        mock_args.agent_name = None

        result = command.run(mock_args)

        assert not result.success
        assert "Agent name is required" in result.message

    def test_view_agent_not_found(self, command, mock_args, mock_deployment_service):
        """Test viewing non-existent agent."""
        mock_deployment_service.get_agent_details.side_effect = Exception(
            "Agent not found"
        )

        mock_args.agents_command = "view"
        mock_args.agent_name = "nonexistent"

        result = command.run(mock_args)

        assert not result.success
        assert "Error viewing agent" in result.message

    def test_view_agent_json_format(self, command, mock_args):
        """Test viewing agent in JSON format."""
        mock_args.agents_command = "view"
        mock_args.agent_name = "engineer"
        mock_args.format = "json"

        result = command.run(mock_args)

        assert result.success
        assert result.data["name"] == "Engineer"
        assert result.data["version"] == "1.0.0"


class TestFixOperations(TestAgentsCommand):
    """Test fix operations for agents."""

    def test_fix_agents_success(self, command, mock_args):
        """Test fixing agent deployment issues."""
        mock_args.agents_command = "fix"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Agent deployment fixed" in result.message
        mock_print.assert_any_call("✓ Agent deployment issues fixed")
        mock_print.assert_any_call("  - Fixed frontmatter formatting")

    def test_fix_agents_no_issues(self, command, mock_args, mock_deployment_service):
        """Test fix when no issues exist."""
        mock_deployment_service.fix_deployment.return_value = {
            "fixes_applied": [],
        }

        mock_args.agents_command = "fix"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        mock_print.assert_any_call("✓ Agent deployment issues fixed")

    def test_fix_agents_json_format(self, command, mock_args):
        """Test fix command with JSON output."""
        mock_args.agents_command = "fix"
        mock_args.format = "json"

        result = command.run(mock_args)

        assert result.success
        assert len(result.data["fixes_applied"]) == 2


class TestDependencyOperations(TestAgentsCommand):
    """Test dependency operations for agents."""

    def test_check_dependencies(self, command, mock_args):
        """Test checking agent dependencies."""
        mock_args.agents_command = "deps-check"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Dependency check completed" in result.message
        mock_print.assert_any_call("Agent Dependencies Check:")
        mock_print.assert_any_call("Missing dependencies:")
        mock_print.assert_any_call("  - numpy")

    def test_check_dependencies_all_satisfied(
        self, command, mock_args, mock_deployment_service
    ):
        """Test checking dependencies when all are satisfied."""
        mock_deployment_service.check_dependencies.return_value = {
            "missing_dependencies": [],
        }

        mock_args.agents_command = "deps-check"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        mock_print.assert_any_call("✓ All dependencies satisfied")

    def test_install_dependencies(self, command, mock_args):
        """Test installing agent dependencies."""
        mock_args.agents_command = "deps-install"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Installed 2 dependencies" in result.message
        mock_print.assert_any_call("✓ Installed 2 dependencies")

    def test_install_dependencies_none_needed(
        self, command, mock_args, mock_deployment_service
    ):
        """Test installing when no dependencies are needed."""
        mock_deployment_service.install_dependencies.return_value = {
            "installed_count": 0,
            "installed": [],
        }

        mock_args.agents_command = "deps-install"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        mock_print.assert_any_call("No dependencies needed installation")

    def test_list_dependencies(self, command, mock_args):
        """Test listing agent dependencies."""
        mock_args.agents_command = "deps-list"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Listed 3 dependencies" in result.message
        mock_print.assert_any_call("Agent Dependencies:")
        mock_print.assert_any_call("✓ numpy")
        mock_print.assert_any_call("✓ pandas")
        mock_print.assert_any_call("✗ scipy")

    def test_list_dependencies_json_format(self, command, mock_args):
        """Test listing dependencies in JSON format."""
        mock_args.agents_command = "deps-list"
        mock_args.format = "json"

        result = command.run(mock_args)

        assert result.success
        assert len(result.data["dependencies"]) == 3
        assert result.data["dependencies"][0]["name"] == "numpy"

    def test_fix_dependencies(self, command, mock_args):
        """Test fixing dependency issues."""
        mock_args.agents_command = "deps-fix"

        with patch("builtins.print") as mock_print:
            result = command.run(mock_args)

        assert result.success
        assert "Dependency issues fixed" in result.message
        mock_print.assert_any_call("✓ Agent dependency issues fixed")
        mock_print.assert_any_call("  - Installed numpy")


class TestErrorHandling(TestAgentsCommand):
    """Test error handling in agent operations."""

    def test_deployment_service_import_error(self, mock_args):
        """Test handling of deployment service import error."""
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.deployed = False
        mock_args.by_tier = False

        with patch(
            "claude_mpm.services.AgentDeploymentService", side_effect=ImportError
        ):
            cmd = AgentsCommand()
            result = cmd.run(mock_args)

        assert not result.success
        assert "Agent deployment service not available" in result.message

    def test_unknown_command(self, command, mock_args):
        """Test handling of unknown command."""
        mock_args.agents_command = "unknown-command"

        result = command.run(mock_args)

        assert not result.success
        assert "Unknown agent command: unknown-command" in result.message

    def test_general_exception_handling(
        self, command, mock_args, mock_deployment_service
    ):
        """Test general exception handling."""
        mock_deployment_service.list_available_agents.side_effect = Exception(
            "Unexpected error"
        )

        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.deployed = False
        mock_args.by_tier = False

        result = command.run(mock_args)

        assert not result.success
        assert "Error listing system agents" in result.message


class TestDefaultBehavior(TestAgentsCommand):
    """Test default behavior when no subcommand is specified."""

    def test_show_agent_versions_default(self, command, mock_args):
        """Test default behavior shows agent versions."""
        mock_args.agents_command = None

        with patch(
            "claude_mpm.cli.commands.agents.get_agent_versions_display"
        ) as mock_get_versions:
            mock_get_versions.return_value = "Engineer v1.0.0\nQA v1.0.0"

            with patch("builtins.print") as mock_print:
                result = command.run(mock_args)

            assert result.success
            mock_print.assert_any_call("Engineer v1.0.0\nQA v1.0.0")

    def test_show_agent_versions_no_agents(self, command, mock_args):
        """Test default behavior when no agents are deployed."""
        mock_args.agents_command = None

        with patch(
            "claude_mpm.cli.commands.agents.get_agent_versions_display"
        ) as mock_get_versions:
            mock_get_versions.return_value = None

            with patch("builtins.print") as mock_print:
                result = command.run(mock_args)

            assert result.success
            mock_print.assert_any_call("No deployed agents found")
            mock_print.assert_any_call(
                "\nTo deploy agents, run: claude-mpm --mpm:agents deploy"
            )

    def test_show_agent_versions_json_format(self, command, mock_args):
        """Test default behavior with JSON output."""
        mock_args.agents_command = None
        mock_args.format = "json"

        with patch(
            "claude_mpm.cli.commands.agents.get_agent_versions_display"
        ) as mock_get_versions:
            mock_get_versions.return_value = "Engineer v1.0.0"

            result = command.run(mock_args)

        assert result.success
        assert result.data["has_agents"] is True
        assert result.data["agent_versions"] == "Engineer v1.0.0"


class TestManageAgentsFunction:
    """Test the manage_agents entry point function."""

    def test_manage_agents_success(self):
        """Test successful execution of manage_agents."""
        mock_args = MagicMock()
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.format = "text"

        with patch.object(AgentsCommand, "execute") as mock_execute:
            mock_execute.return_value = CommandResult.success_result("Success")

            exit_code = manage_agents(mock_args)

        assert exit_code == 0
        mock_execute.assert_called_once_with(mock_args)

    def test_manage_agents_with_json_output(self):
        """Test manage_agents with JSON output format."""
        mock_args = MagicMock()
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.format = "json"

        with patch.object(AgentsCommand, "execute") as mock_execute:
            with patch.object(AgentsCommand, "print_result") as mock_print:
                mock_result = CommandResult.success_result(
                    "Success", data={"test": "data"}
                )
                mock_execute.return_value = mock_result

                exit_code = manage_agents(mock_args)

            assert exit_code == 0
            mock_print.assert_called_once_with(mock_result, mock_args)

    def test_manage_agents_failure(self):
        """Test manage_agents with failure."""
        mock_args = MagicMock()
        mock_args.agents_command = "deploy"
        mock_args.format = "text"

        with patch.object(AgentsCommand, "execute") as mock_execute:
            mock_execute.return_value = CommandResult.error_result(
                "Failed", exit_code=1
            )

            exit_code = manage_agents(mock_args)

        assert exit_code == 1


class TestLazyLoading:
    """Test lazy loading of deployment service."""

    def test_deployment_service_lazy_loading(self):
        """Test that deployment service is loaded lazily."""
        cmd = AgentsCommand()

        # Service should not be initialized yet
        assert cmd._deployment_service is None

        with patch("claude_mpm.services.AgentDeploymentService") as MockService:
            with patch(
                "claude_mpm.services.agents.deployment.deployment_wrapper.DeploymentServiceWrapper"
            ) as MockWrapper:
                # Access the property
                service = cmd.deployment_service

                # Service should now be initialized
                assert service is not None
                MockService.assert_called_once()
                MockWrapper.assert_called_once()

    def test_deployment_service_cached(self):
        """Test that deployment service is cached after first access."""
        cmd = AgentsCommand()

        with patch("claude_mpm.services.AgentDeploymentService") as MockService:
            with patch(
                "claude_mpm.services.agents.deployment.deployment_wrapper.DeploymentServiceWrapper"
            ) as MockWrapper:
                mock_wrapper = MagicMock()
                MockWrapper.return_value = mock_wrapper

                # First access
                service1 = cmd.deployment_service
                # Second access
                service2 = cmd.deployment_service

                # Should be the same instance
                assert service1 is service2
                # Should only be created once
                MockService.assert_called_once()
                MockWrapper.assert_called_once()


class TestOutputFormats:
    """Test different output formats for agent commands."""

    @pytest.fixture
    def command_with_service(self, mock_deployment_service):
        """Create command with mocked service."""
        cmd = AgentsCommand()
        cmd._deployment_service = mock_deployment_service
        return cmd

    @pytest.mark.parametrize("format_type", ["json", "yaml", "text"])
    def test_list_agents_formats(self, command_with_service, format_type):
        """Test list agents with different output formats."""
        mock_args = MagicMock()
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.format = format_type
        mock_args.deployed = False
        mock_args.by_tier = False

        result = command_with_service.run(mock_args)

        assert result.success
        if format_type in ["json", "yaml"]:
            assert result.data is not None
            assert "agents" in result.data
            assert "count" in result.data

    @pytest.mark.parametrize("format_type", ["json", "yaml", "text"])
    def test_deploy_agents_formats(self, command_with_service, format_type):
        """Test deploy agents with different output formats."""
        mock_args = MagicMock()
        mock_args.agents_command = "deploy"
        mock_args.format = format_type

        result = command_with_service.run(mock_args)

        assert result.success
        if format_type in ["json", "yaml"]:
            assert result.data is not None
            assert "total_deployed" in result.data


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def command_with_service(self, mock_deployment_service):
        """Create command with mocked service."""
        cmd = AgentsCommand()
        cmd._deployment_service = mock_deployment_service
        return cmd

    def test_empty_agent_list(self, command_with_service, mock_deployment_service):
        """Test handling of empty agent list."""
        mock_deployment_service.list_available_agents.return_value = []

        mock_args = MagicMock()
        mock_args.agents_command = "list"
        mock_args.system = True
        mock_args.format = "text"
        mock_args.deployed = False
        mock_args.by_tier = False

        with patch("builtins.print") as mock_print:
            result = command_with_service.run(mock_args)

        assert result.success
        mock_print.assert_any_call("No agent templates found")

    def test_cleanup_orphaned_no_directory(self, command_with_service):
        """Test cleanup orphaned when agents directory doesn't exist."""
        mock_args = MagicMock()
        mock_args.agents_command = "cleanup-orphaned"
        mock_args.agents_dir = None
        mock_args.dry_run = True
        mock_args.force = False

        with patch("pathlib.Path.exists", return_value=False):
            result = command_with_service.run(mock_args)

        assert result.success
        assert "Agents directory not found" in result.message

    def test_cleanup_orphaned_with_errors(self, command_with_service):
        """Test cleanup orphaned with errors during removal."""
        mock_args = MagicMock()
        mock_args.agents_command = "cleanup-orphaned"
        mock_args.force = True
        mock_args.dry_run = False
        mock_args.quiet = False
        mock_args.format = "text"

        with patch(
            "claude_mpm.services.agents.deployment.multi_source_deployment_service.MultiSourceAgentDeploymentService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.cleanup_orphaned_agents.return_value = {
                "orphaned": [{"name": "test", "version": "1.0"}],
                "removed": [],
                "errors": ["Permission denied", "File locked"],
            }

            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.print") as mock_print:
                    result = command_with_service.run(mock_args)

            assert not result.success
            assert "Cleanup completed with 2 errors" in result.message
            mock_print.assert_any_call("❌ Encountered 2 error(s):")

    def test_view_agent_special_characters(self, command_with_service):
        """Test viewing agent with special characters in name."""
        mock_args = MagicMock()
        mock_args.agents_command = "view"
        mock_args.agent_name = "test-agent_v2.0"
        mock_args.format = "text"

        result = command_with_service.run(mock_args)

        assert result.success
        command_with_service._deployment_service.get_agent_details.assert_called_once_with(
            "test-agent_v2.0"
        )


class TestCompatibility:
    """Test backward compatibility with legacy functions."""

    @patch("claude_mpm.cli.commands.agents.AgentRegistryAdapter")
    def test_legacy_list_agents_by_tier(self, mock_adapter):
        """Test legacy _list_agents_by_tier function."""
        from claude_mpm.cli.commands.agents import _list_agents_by_tier

        mock_registry = MagicMock()
        mock_adapter.return_value.registry = mock_registry
        mock_registry.list_agents.return_value = {
            "engineer": {"tier": "project", "description": "Test"},
            "qa": {"tier": "system", "path": "/path/qa.md"},
        }

        with patch("builtins.print"):
            _list_agents_by_tier()

        mock_registry.list_agents.assert_called_once()

    @patch("claude_mpm.cli.commands.agents.AgentRegistryAdapter")
    def test_legacy_view_agent(self, mock_adapter):
        """Test legacy _view_agent function."""
        from claude_mpm.cli.commands.agents import _view_agent

        mock_args = MagicMock()
        mock_args.agent_name = "test"

        mock_registry = MagicMock()
        mock_adapter.return_value.registry = mock_registry

        mock_agent = MagicMock()
        mock_agent.name = "test"
        mock_agent.type = "standard"
        mock_agent.tier = "system"
        mock_agent.path = "/path/test.md"
        mock_agent.description = "Test agent"
        mock_agent.specializations = ["testing"]

        mock_registry.get_agent.return_value = mock_agent

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = (
                    "---\nname: test\nversion: 1.0.0\n---\nInstructions here"
                )
                with patch("builtins.print"):
                    _view_agent(mock_args)

        mock_registry.get_agent.assert_called_once_with("test")

    def test_legacy_deploy_agents(self):
        """Test legacy _deploy_agents function."""
        from claude_mpm.cli.commands.agents import _deploy_agents

        mock_args = MagicMock()
        mock_args.target = None
        mock_args.include_all = False

        mock_service = MagicMock()
        mock_service.deploy_agents.return_value = {
            "deployed": [{"name": "test"}],
            "updated": [],
            "errors": [],
            "target_dir": "/path/to/agents",
        }
        mock_service.set_claude_environment.return_value = {"CLAUDE_AGENTS": "/path"}

        with patch("claude_mpm.cli.commands.agents.ConfigLoader") as MockLoader:
            with patch("claude_mpm.cli.commands.agents.get_logger"):
                with patch("builtins.print"):
                    with patch("pathlib.Path.cwd", return_value=Path("/project")):
                        with patch("pathlib.Path.exists", return_value=False):
                            mock_config = MagicMock()
                            mock_config.get.return_value = []
                            MockLoader.return_value.load_main_config.return_value = (
                                mock_config
                            )

                            _deploy_agents(mock_args, mock_service, force=False)

        mock_service.deploy_agents.assert_called_once()


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    def full_command(self):
        """Create a fully configured command."""
        cmd = AgentsCommand()
        # Don't mock the deployment service to test full integration
        return cmd

    def test_deploy_then_list_workflow(self, mock_deployment_service):
        """Test deploy followed by list workflow."""
        cmd = AgentsCommand()
        cmd._deployment_service = mock_deployment_service

        # Deploy agents
        deploy_args = MagicMock()
        deploy_args.agents_command = "deploy"
        deploy_args.format = "text"

        deploy_result = cmd.run(deploy_args)
        assert deploy_result.success

        # List deployed agents
        list_args = MagicMock()
        list_args.agents_command = "list"
        list_args.deployed = True
        list_args.system = False
        list_args.by_tier = False
        list_args.format = "text"

        list_result = cmd.run(list_args)
        assert list_result.success

        # Verify both operations were called
        mock_deployment_service.deploy_system_agents.assert_called_once()
        mock_deployment_service.verify_deployment.assert_called_once()

    def test_check_install_verify_dependencies_workflow(self, mock_deployment_service):
        """Test complete dependency management workflow."""
        cmd = AgentsCommand()
        cmd._deployment_service = mock_deployment_service

        # Check dependencies
        check_args = MagicMock()
        check_args.agents_command = "deps-check"
        check_args.format = "text"

        check_result = cmd.run(check_args)
        assert check_result.success

        # Install missing dependencies
        install_args = MagicMock()
        install_args.agents_command = "deps-install"
        install_args.format = "text"

        install_result = cmd.run(install_args)
        assert install_result.success

        # Verify dependencies again
        mock_deployment_service.check_dependencies.return_value = {
            "missing_dependencies": []
        }

        verify_result = cmd.run(check_args)
        assert verify_result.success

        assert mock_deployment_service.check_dependencies.call_count == 2
        mock_deployment_service.install_dependencies.assert_called_once()
