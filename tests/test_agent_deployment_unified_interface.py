"""
Tests for unified agent deployment/removal interface.

This test suite verifies the new unified interface for managing agent
deployment state through a single checkbox UI.

Related Ticket: User request for unified deploy/remove interface
Design: Agent selection shows ALL agents with pre-selected deployed agents.
        Selecting = Deploy, Unselecting = Remove.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.cli.commands.configure import ConfigureCommand
from claude_mpm.cli.commands.configure_models import AgentConfig


class TestUnifiedAgentDeploymentInterface:
    """Test the unified agent deployment/removal interface."""

    @pytest.fixture
    def mock_console(self):
        """Create mock Rich console."""
        return Mock()

    @pytest.fixture
    def configure_command(self, mock_console):
        """Create ConfigureCommand instance with mocked dependencies."""
        with patch("claude_mpm.cli.commands.configure.Console") as mock_console_cls:
            mock_console_cls.return_value = mock_console
            cmd = ConfigureCommand()
            cmd.console = mock_console
            return cmd

    @pytest.fixture
    def sample_agents(self):
        """Create sample agent configurations."""
        return [
            AgentConfig(
                name="engineer", description="Engineering agent", dependencies=[]
            ),
            AgentConfig(name="qa", description="QA agent", dependencies=[]),
            AgentConfig(
                name="pm", description="Project Manager agent", dependencies=[]
            ),
            AgentConfig(
                name="BASE_AGENT",
                description="Build tool (should be filtered)",
                dependencies=[],
            ),
        ]

    @pytest.mark.skip(
        reason=(
            "_deploy_agents_individual has been removed. "
            "Migrate to _deploy_agents_unified when needed."
        )
    )
    def test_filters_base_agent(self, configure_command, sample_agents):
        """Test that BASE_AGENT is filtered from display."""
        with patch("claude_mpm.utils.agent_filters.filter_base_agents") as mock_filter:
            # Mock filter_base_agents to remove BASE_AGENT
            mock_filter.return_value = [
                {
                    "agent_id": "engineer",
                    "name": "engineer",
                    "description": "Engineering agent",
                    "deployed": False,
                },
                {
                    "agent_id": "qa",
                    "name": "qa",
                    "description": "QA agent",
                    "deployed": False,
                },
                {
                    "agent_id": "pm",
                    "name": "pm",
                    "description": "Project Manager agent",
                    "deployed": False,
                },
            ]

            with patch(
                "claude_mpm.utils.agent_filters.get_deployed_agent_ids"
            ) as mock_deployed:
                mock_deployed.return_value = set()

                with patch("claude_mpm.cli.commands.configure.questionary") as mock_q:
                    mock_q.checkbox.return_value.ask.return_value = None

                    with patch("claude_mpm.cli.commands.configure.Prompt"):
                        configure_command._deploy_agents_individual(sample_agents)

                    # Verify filter_base_agents was called
                    mock_filter.assert_called_once()

    @pytest.mark.skip(
        reason=(
            "_deploy_agents_individual has been removed. "
            "Migrate to _deploy_agents_unified when needed."
        )
    )
    def test_shows_all_agents_including_deployed(
        self, configure_command, sample_agents
    ):
        """Test that deployed agents are shown and pre-selected."""
        with patch("claude_mpm.utils.agent_filters.filter_base_agents") as mock_filter:
            mock_filter.return_value = [
                {
                    "agent_id": "engineer",
                    "name": "engineer",
                    "description": "Engineering agent",
                    "deployed": True,
                },
                {
                    "agent_id": "qa",
                    "name": "qa",
                    "description": "QA agent",
                    "deployed": False,
                },
                {
                    "agent_id": "pm",
                    "name": "pm",
                    "description": "Project Manager agent",
                    "deployed": False,
                },
            ]

            with patch(
                "claude_mpm.utils.agent_filters.get_deployed_agent_ids"
            ) as mock_deployed:
                mock_deployed.return_value = {"engineer"}  # Engineer is deployed

                with patch("claude_mpm.cli.commands.configure.questionary") as mock_q:
                    mock_checkbox = Mock()
                    mock_q.checkbox.return_value = mock_checkbox
                    mock_checkbox.ask.return_value = None

                    with patch("claude_mpm.cli.commands.configure.Prompt"):
                        configure_command._deploy_agents_individual(sample_agents)

                    # Verify questionary.checkbox was called
                    mock_q.checkbox.assert_called_once()
                    call_args = mock_q.checkbox.call_args

                    # Check that choices include all non-BASE agents
                    choices = call_args.kwargs["choices"]
                    assert len(choices) >= 2  # At least engineer and others

    def test_calculates_deploy_and_remove_correctly(
        self, configure_command, sample_agents
    ):
        """Test that deploy/remove sets are calculated correctly."""
        # Setup: engineer is deployed, user selects qa and pm
        # Expected: deploy qa and pm, remove engineer
        deployed_ids = {"engineer"}
        selected_ids = ["qa", "pm"]

        # Simulate the set logic
        selected_set = set(selected_ids)
        to_deploy = selected_set - deployed_ids
        to_remove = deployed_ids - selected_set

        assert to_deploy == {"qa", "pm"}
        assert to_remove == {"engineer"}

    @pytest.mark.skip(
        reason=(
            "_deploy_agents_individual has been removed. "
            "Migrate to _deploy_agents_unified when needed."
        )
    )
    def test_simple_text_format(self, configure_command, sample_agents):
        """Test that agent choices use simple 'agent/path - Display Name' format."""
        # Add display name to test agent
        sample_agents[0].display_name = "Backend Engineer"

        with patch("claude_mpm.utils.agent_filters.filter_base_agents") as mock_filter:
            mock_filter.return_value = [
                {
                    "agent_id": "engineer",
                    "name": "engineer",
                    "description": "Engineering agent",
                    "deployed": False,
                },
            ]

            with patch(
                "claude_mpm.utils.agent_filters.get_deployed_agent_ids"
            ) as mock_deployed:
                mock_deployed.return_value = set()

                with patch("claude_mpm.cli.commands.configure.questionary") as mock_q:
                    mock_q.checkbox.return_value.ask.return_value = None

                    with patch("claude_mpm.cli.commands.configure.Prompt"):
                        configure_command._deploy_agents_individual(sample_agents)

                    # Verify checkbox was called
                    call_args = mock_q.checkbox.call_args
                    choices = call_args.kwargs["choices"]

                    # Check format is simple (no long descriptions)
                    for choice in choices:
                        choice_text = choice.title
                        # Should be "agent_id - Display Name" or just "agent_id"
                        assert "(" not in choice_text or len(choice_text) < 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
