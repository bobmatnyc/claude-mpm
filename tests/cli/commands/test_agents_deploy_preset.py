"""Integration tests for preset-based agent deployment.

Tests the `claude-mpm agents deploy --preset <name>` command flow.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.claude_mpm.cli.commands.agents import AgentsCommand


class TestAgentsDeployPreset:
    """Integration tests for preset deployment command."""

    @pytest.fixture
    def agents_command(self):
        """Create AgentsCommand instance."""
        return AgentsCommand()

    @pytest.fixture
    def mock_args_minimal(self, mocker):
        """Create mock args for minimal preset."""
        args = mocker.Mock()
        args.preset = "minimal"
        args.dry_run = False
        args.force = False
        args.agents_command = "deploy"
        return args

    @pytest.fixture
    def mock_args_invalid_preset(self, mocker):
        """Create mock args with invalid preset."""
        args = mocker.Mock()
        args.preset = "invalid-preset-name"
        args.dry_run = False
        args.force = False
        args.agents_command = "deploy"
        return args

    @pytest.fixture
    def mock_args_dry_run(self, mocker):
        """Create mock args for dry-run mode."""
        args = mocker.Mock()
        args.preset = "python-dev"
        args.dry_run = True
        args.force = False
        args.agents_command = "deploy"
        return args

    def test_deploy_with_valid_preset(
        self, agents_command, mock_args_minimal, mocker, capsys
    ):
        """Test deploying with valid preset."""
        # Mock services
        mock_config = mocker.patch(
            "src.claude_mpm.cli.commands.agents.AgentSourceConfiguration"
        )
        mock_config.load.return_value = mocker.Mock()

        mock_git_manager = mocker.patch(
            "src.claude_mpm.cli.commands.agents.GitSourceManager"
        )
        mock_git_manager_instance = mocker.Mock()
        mock_git_manager.return_value = mock_git_manager_instance

        # Mock cached agents (all available)
        mock_git_manager_instance.list_cached_agents.return_value = [
            {
                "agent_id": "universal/memory-manager",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Memory Manager"},
            },
            {
                "agent_id": "universal/research",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Research"},
            },
            {
                "agent_id": "documentation/documentation",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Documentation"},
            },
            {
                "agent_id": "engineer/backend/python-engineer",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Python Engineer"},
            },
            {
                "agent_id": "qa/qa",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "QA"},
            },
            {
                "agent_id": "ops/core/ops",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Ops"},
            },
        ]

        # Mock deployment service
        mock_deployment = mocker.patch(
            "src.claude_mpm.cli.commands.agents.SingleTierDeploymentService"
        )
        mock_deployment_instance = mocker.Mock()
        mock_deployment.return_value = mock_deployment_instance

        # Mock successful deployments
        mock_deployment_instance.deploy_agent.return_value = {
            "deployed": True,
            "agent_name": "test-agent",
            "source": "test-repo",
            "priority": 100,
            "path": "/path/to/agent.md",
        }

        # Execute command
        result = agents_command._deploy_preset(mock_args_minimal)

        # Verify success
        assert result.success
        assert "minimal" in result.message

        # Verify output
        captured = capsys.readouterr()
        assert "Resolving preset: minimal" in captured.out
        assert "6 core agents" in captured.out
        assert "Deploying" in captured.out

    def test_deploy_with_invalid_preset(
        self, agents_command, mock_args_invalid_preset, capsys
    ):
        """Test deploying with invalid preset shows available presets."""
        # Execute command
        result = agents_command._deploy_preset(mock_args_invalid_preset)

        # Verify error
        assert not result.success
        assert "Unknown preset" in result.message

        # Verify available presets shown
        captured = capsys.readouterr()
        assert "Available presets:" in captured.out
        assert "minimal:" in captured.out
        assert "python-dev:" in captured.out

    def test_deploy_dry_run(self, agents_command, mock_args_dry_run, mocker, capsys):
        """Test dry-run mode shows preview without deploying."""
        # Mock services
        mock_config = mocker.patch(
            "src.claude_mpm.cli.commands.agents.AgentSourceConfiguration"
        )
        mock_config.load.return_value = mocker.Mock()

        mock_git_manager = mocker.patch(
            "src.claude_mpm.cli.commands.agents.GitSourceManager"
        )
        mock_git_manager_instance = mocker.Mock()
        mock_git_manager.return_value = mock_git_manager_instance

        # Mock cached agents
        mock_git_manager_instance.list_cached_agents.return_value = [
            {
                "agent_id": "universal/memory-manager",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Memory Manager"},
            },
        ]

        mock_deployment = mocker.patch(
            "src.claude_mpm.cli.commands.agents.SingleTierDeploymentService"
        )

        # Execute command
        result = agents_command._deploy_preset(mock_args_dry_run)

        # Verify dry run success
        assert result.success
        assert "Dry run complete" in result.message

        # Verify output
        captured = capsys.readouterr()
        assert "DRY RUN:" in captured.out
        assert "Preview agent deployment" in captured.out
        assert "without --dry-run" in captured.out

        # Verify no actual deployment happened
        mock_deployment_instance = mock_deployment.return_value
        assert not mock_deployment_instance.deploy_agent.called

    def test_deploy_with_missing_agents(
        self, agents_command, mock_args_minimal, mocker, capsys
    ):
        """Test deployment handles missing agents gracefully."""
        # Mock services
        mock_config = mocker.patch(
            "src.claude_mpm.cli.commands.agents.AgentSourceConfiguration"
        )
        mock_config.load.return_value = mocker.Mock()

        mock_git_manager = mocker.patch(
            "src.claude_mpm.cli.commands.agents.GitSourceManager"
        )
        mock_git_manager_instance = mocker.Mock()
        mock_git_manager.return_value = mock_git_manager_instance

        # Mock only 2 out of 6 agents available
        mock_git_manager_instance.list_cached_agents.return_value = [
            {
                "agent_id": "universal/memory-manager",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Memory Manager"},
            },
            {
                "agent_id": "universal/research",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Research"},
            },
        ]

        mock_deployment = mocker.patch(
            "src.claude_mpm.cli.commands.agents.SingleTierDeploymentService"
        )
        mock_deployment_instance = mocker.Mock()
        mock_deployment.return_value = mock_deployment_instance

        mock_deployment_instance.deploy_agent.return_value = {
            "deployed": True,
            "agent_name": "test-agent",
        }

        # Execute command
        result = agents_command._deploy_preset(mock_args_minimal)

        # Should still succeed with partial deployment
        assert result.success

        # Verify warning shown
        captured = capsys.readouterr()
        assert "Missing agents" in captured.out
        assert "not found in configured sources" in captured.out

    def test_deploy_with_conflicts(
        self, agents_command, mock_args_minimal, mocker, capsys
    ):
        """Test deployment shows warnings for source conflicts."""
        # Mock services
        mock_config = mocker.patch(
            "src.claude_mpm.cli.commands.agents.AgentSourceConfiguration"
        )
        mock_config.load.return_value = mocker.Mock()

        mock_git_manager = mocker.patch(
            "src.claude_mpm.cli.commands.agents.GitSourceManager"
        )
        mock_git_manager_instance = mocker.Mock()
        mock_git_manager.return_value = mock_git_manager_instance

        # Mock same agent in multiple sources
        mock_git_manager_instance.list_cached_agents.return_value = [
            {
                "agent_id": "universal/memory-manager",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "Memory Manager A"},
            },
            {
                "agent_id": "universal/memory-manager",
                "source": {"identifier": "repo-b"},
                "metadata": {"name": "Memory Manager B"},
            },
            {
                "agent_id": "universal/research",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "Research"},
            },
            {
                "agent_id": "documentation/documentation",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "Documentation"},
            },
            {
                "agent_id": "engineer/backend/python-engineer",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "Python Engineer"},
            },
            {
                "agent_id": "qa/qa",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "QA"},
            },
            {
                "agent_id": "ops/core/ops",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "Ops"},
            },
        ]

        mock_deployment = mocker.patch(
            "src.claude_mpm.cli.commands.agents.SingleTierDeploymentService"
        )
        mock_deployment_instance = mocker.Mock()
        mock_deployment.return_value = mock_deployment_instance

        mock_deployment_instance.deploy_agent.return_value = {"deployed": True}

        # Execute command
        result = agents_command._deploy_preset(mock_args_minimal)

        # Verify conflict warning shown
        captured = capsys.readouterr()
        assert "Priority conflicts detected" in captured.out
        assert "universal/memory-manager" in captured.out
        assert "Using highest priority source" in captured.out

    def test_deploy_deployment_failure(
        self, agents_command, mock_args_minimal, mocker, capsys
    ):
        """Test handling of deployment failures."""
        # Mock services
        mock_config = mocker.patch(
            "src.claude_mpm.cli.commands.agents.AgentSourceConfiguration"
        )
        mock_config.load.return_value = mocker.Mock()

        mock_git_manager = mocker.patch(
            "src.claude_mpm.cli.commands.agents.GitSourceManager"
        )
        mock_git_manager_instance = mocker.Mock()
        mock_git_manager.return_value = mock_git_manager_instance

        mock_git_manager_instance.list_cached_agents.return_value = [
            {
                "agent_id": "universal/memory-manager",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Memory Manager"},
            },
        ]

        mock_deployment = mocker.patch(
            "src.claude_mpm.cli.commands.agents.SingleTierDeploymentService"
        )
        mock_deployment_instance = mocker.Mock()
        mock_deployment.return_value = mock_deployment_instance

        # Mock deployment failure
        mock_deployment_instance.deploy_agent.return_value = {
            "deployed": False,
            "error": "Permission denied",
        }

        # Execute command
        result = agents_command._deploy_preset(mock_args_minimal)

        # Should fail
        assert not result.success
        assert "No agents deployed" in result.message

        # Verify error shown
        captured = capsys.readouterr()
        assert "Failed agents:" in captured.out
        assert "Permission denied" in captured.out
