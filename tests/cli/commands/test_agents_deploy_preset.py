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
    def mock_args_minimal(self):
        """Create mock args for minimal preset."""
        args = MagicMock()
        args.preset = "minimal"
        args.dry_run = False
        args.force = False
        args.agents_command = "deploy"
        return args

    @pytest.fixture
    def mock_args_invalid_preset(self):
        """Create mock args with invalid preset."""
        args = MagicMock()
        args.preset = "invalid-preset-name"
        args.dry_run = False
        args.force = False
        args.agents_command = "deploy"
        return args

    @pytest.fixture
    def mock_args_dry_run(self):
        """Create mock args for dry-run mode."""
        args = MagicMock()
        args.preset = "python-dev"
        args.dry_run = True
        args.force = False
        args.agents_command = "deploy"
        return args

    def test_deploy_with_valid_preset(self, agents_command, mock_args_minimal, capsys):
        """Test deploying with valid preset."""
        from unittest.mock import MagicMock, patch

        # Mock services using context managers
        with patch(
            "src.claude_mpm.config.agent_sources.AgentSourceConfiguration"
        ) as mock_config_class, patch(
            "src.claude_mpm.services.agents.git_source_manager.GitSourceManager"
        ) as mock_git_manager_class, patch(
            "src.claude_mpm.services.agents.single_tier_deployment_service.SingleTierDeploymentService"
        ) as mock_deployment_class, patch(
            "src.claude_mpm.services.agents.agent_preset_service.AgentPresetService"
        ) as mock_preset_service_class:
            # Setup mocks
            mock_config_class.load.return_value = MagicMock()

            mock_git_manager_instance = MagicMock()
            mock_git_manager_class.return_value = mock_git_manager_instance

            # Mock preset service
            mock_preset_service = MagicMock()
            mock_preset_service_class.return_value = mock_preset_service

            # Mock preset validation
            mock_preset_service.validate_preset.return_value = True

            # Mock preset resolution with 9 agents
            mock_preset_service.resolve_agents.return_value = {
                "preset_info": {
                    "name": "minimal",
                    "description": "Core agents only - universal starter kit",
                    "agent_count": 9,
                    "use_cases": ["Any project type", "Quick start", "Learning"],
                },
                "agents": [
                    {"agent_id": "claude-mpm/mpm-agent-manager", "source": "test-repo"},
                    {
                        "agent_id": "claude-mpm/mpm-skills-manager",
                        "source": "test-repo",
                    },
                    {"agent_id": "engineer/core/engineer", "source": "test-repo"},
                    {"agent_id": "universal/research", "source": "test-repo"},
                    {"agent_id": "qa/qa", "source": "test-repo"},
                    {"agent_id": "qa/web-qa", "source": "test-repo"},
                    {"agent_id": "documentation/documentation", "source": "test-repo"},
                    {"agent_id": "ops/core/ops", "source": "test-repo"},
                    {"agent_id": "documentation/ticketing", "source": "test-repo"},
                ],
                "missing_agents": [],
                "conflicts": [],
            }

            # Mock cached agents (not used when AgentPresetService is mocked, but kept for compatibility)
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
            mock_deployment_instance = MagicMock()
            mock_deployment_class.return_value = mock_deployment_instance

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
            assert "Agents: 9" in captured.out
            assert "Deploying 9 agents" in captured.out

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

    def test_deploy_dry_run(self, agents_command, mock_args_dry_run, capsys):
        """Test dry-run mode shows preview without deploying."""
        from unittest.mock import MagicMock, patch

        with patch(
            "src.claude_mpm.config.agent_sources.AgentSourceConfiguration"
        ) as mock_config_class, patch(
            "src.claude_mpm.services.agents.git_source_manager.GitSourceManager"
        ) as mock_git_manager_class, patch(
            "src.claude_mpm.services.agents.single_tier_deployment_service.SingleTierDeploymentService"
        ) as mock_deployment_class:
            # Setup mocks
            mock_config_class.load.return_value = MagicMock()

            mock_git_manager_instance = MagicMock()
            mock_git_manager_class.return_value = mock_git_manager_instance

            # Mock cached agents
            mock_git_manager_instance.list_cached_agents.return_value = [
                {
                    "agent_id": "universal/memory-manager",
                    "source": {"identifier": "test-repo"},
                    "metadata": {"name": "Memory Manager"},
                },
            ]

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
            mock_deployment_instance = mock_deployment_class.return_value
            assert not mock_deployment_instance.deploy_agent.called

    def test_deploy_with_missing_agents(
        self, agents_command, mock_args_minimal, capsys
    ):
        """Test deployment handles missing agents gracefully."""
        from unittest.mock import MagicMock, patch

        with patch(
            "src.claude_mpm.config.agent_sources.AgentSourceConfiguration"
        ) as mock_config_class, patch(
            "src.claude_mpm.services.agents.git_source_manager.GitSourceManager"
        ) as mock_git_manager_class, patch(
            "src.claude_mpm.services.agents.single_tier_deployment_service.SingleTierDeploymentService"
        ) as mock_deployment_class:
            # Setup mocks
            mock_config_class.load.return_value = MagicMock()

            mock_git_manager_instance = MagicMock()
            mock_git_manager_class.return_value = mock_git_manager_instance

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

            # Mock deployment service
            mock_deployment_instance = MagicMock()
            mock_deployment_class.return_value = mock_deployment_instance

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

    def test_deploy_with_conflicts(self, agents_command, mock_args_minimal, capsys):
        """Test deployment shows warnings for source conflicts."""
        from unittest.mock import MagicMock, patch

        with patch(
            "src.claude_mpm.config.agent_sources.AgentSourceConfiguration"
        ) as mock_config_class, patch(
            "src.claude_mpm.services.agents.git_source_manager.GitSourceManager"
        ) as mock_git_manager_class, patch(
            "src.claude_mpm.services.agents.single_tier_deployment_service.SingleTierDeploymentService"
        ) as mock_deployment_class, patch(
            "src.claude_mpm.services.agents.agent_preset_service.AgentPresetService"
        ) as mock_preset_service_class:
            # Setup mocks
            mock_config_class.load.return_value = MagicMock()

            mock_git_manager_instance = MagicMock()
            mock_git_manager_class.return_value = mock_git_manager_instance

            # Mock preset service
            mock_preset_service = MagicMock()
            mock_preset_service_class.return_value = mock_preset_service

            # Mock preset validation
            mock_preset_service.validate_preset.return_value = True

            # Mock preset resolution with conflicts
            mock_preset_service.resolve_agents.return_value = {
                "preset_info": {
                    "name": "minimal",
                    "description": "Core agents only - universal starter kit",
                    "agent_count": 9,
                    "use_cases": ["Any project type", "Quick start", "Learning"],
                },
                "agents": [
                    {"agent_id": "claude-mpm/mpm-agent-manager", "source": "repo-a"},
                    {"agent_id": "universal/research", "source": "repo-a"},
                ],
                "missing_agents": [],
                "conflicts": [
                    {
                        "agent_id": "universal/memory-manager",
                        "sources": ["repo-a", "repo-b"],
                    }
                ],
            }

            # Mock deployment service
            mock_deployment_instance = MagicMock()
            mock_deployment_class.return_value = mock_deployment_instance

            mock_deployment_instance.deploy_agent.return_value = {"deployed": True}

            # Execute command
            result = agents_command._deploy_preset(mock_args_minimal)

            # Verify conflict warning shown
            captured = capsys.readouterr()
            assert "Priority conflicts detected" in captured.out
            assert "universal/memory-manager" in captured.out
            assert "Using highest priority source" in captured.out

    def test_deploy_deployment_failure(self, agents_command, mock_args_minimal, capsys):
        """Test handling of deployment failures."""
        from unittest.mock import MagicMock, patch

        with patch(
            "src.claude_mpm.config.agent_sources.AgentSourceConfiguration"
        ) as mock_config_class, patch(
            "src.claude_mpm.services.agents.git_source_manager.GitSourceManager"
        ) as mock_git_manager_class, patch(
            "src.claude_mpm.services.agents.single_tier_deployment_service.SingleTierDeploymentService"
        ) as mock_deployment_class, patch(
            "src.claude_mpm.services.agents.agent_preset_service.AgentPresetService"
        ) as mock_preset_service_class:
            # Setup mocks
            mock_config_class.load.return_value = MagicMock()

            mock_git_manager_instance = MagicMock()
            mock_git_manager_class.return_value = mock_git_manager_instance

            # Mock preset service
            mock_preset_service = MagicMock()
            mock_preset_service_class.return_value = mock_preset_service

            # Mock preset validation
            mock_preset_service.validate_preset.return_value = True

            # Mock preset resolution with one agent
            mock_preset_service.resolve_agents.return_value = {
                "preset_info": {
                    "name": "minimal",
                    "description": "Core agents only - universal starter kit",
                    "agent_count": 9,
                    "use_cases": ["Any project type", "Quick start", "Learning"],
                },
                "agents": [
                    {"agent_id": "universal/memory-manager", "source": "test-repo"},
                ],
                "missing_agents": [],
                "conflicts": [],
            }

            # Mock deployment service
            mock_deployment_instance = MagicMock()
            mock_deployment_class.return_value = mock_deployment_instance

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
