"""Test template discovery and filtering operations.

This module tests agent template discovery, multi-source template resolution,
and template filtering based on exclusion rules.
"""

from pathlib import Path
from unittest.mock import Mock

from conftest import TestAgentDeploymentService


class TestTemplateDiscovery(TestAgentDeploymentService):
    """Test template discovery operations."""

    def test_list_available_agents(self, service, mock_dependencies):
        """Test listing available agent templates."""
        expected_agents = [
            {"name": "agent1", "version": "1.0.0"},
            {"name": "agent2", "version": "2.0.0"},
        ]
        mock_dependencies["discovery_service"].list_available_agents.return_value = (
            expected_agents
        )

        result = service.list_available_agents()

        assert result == expected_agents
        mock_dependencies[
            "discovery_service"
        ].list_available_agents.assert_called_once()

    def test_get_multi_source_templates(self, service, tmp_path, mock_dependencies):
        """Test getting templates from multiple sources."""
        # Setup mock return values
        mock_dependencies[
            "multi_source_service"
        ].get_agents_for_deployment.return_value = (
            {
                "agent1": tmp_path / "system" / "agent1.json",
                "agent2": tmp_path / "project" / "agent2.json",
            },
            {"agent1": "system", "agent2": "project"},
            {"removed": []},
        )

        # Create mock config
        mock_config = Mock()

        templates, sources, cleanup = service._get_multi_source_templates(
            excluded_agents=["excluded_agent"],
            config=mock_config,
            agents_dir=tmp_path / ".claude" / "agents",
        )

        assert len(templates) == 2
        assert "agent1" in sources
        assert sources["agent1"] == "system"

    def test_get_filtered_templates(self, service, mock_dependencies):
        """Test getting filtered templates based on exclusion rules."""
        mock_config = Mock()
        expected_templates = [
            Path("/path/to/agent1.json"),
            Path("/path/to/agent2.json"),
        ]

        mock_dependencies["discovery_service"].get_filtered_templates.return_value = (
            expected_templates
        )

        result = service._get_filtered_templates(["excluded"], mock_config)

        assert result == expected_templates
        mock_dependencies[
            "discovery_service"
        ].get_filtered_templates.assert_called_with(["excluded"], mock_config)

    def test_get_multi_source_templates_with_comparison(
        self, service, tmp_path, mock_dependencies
    ):
        """Test multi-source templates with deployed version comparison."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Create existing deployed agent
        deployed_agent = agents_dir / "existing.md"
        deployed_agent.write_text("---\nname: existing\nversion: 1.0.0\n---\nContent")

        # Setup mock returns
        mock_dependencies[
            "multi_source_service"
        ].get_agents_for_deployment.return_value = (
            {"existing": tmp_path / "templates" / "existing.json"},
            {"existing": "system"},
            {"removed": []},
        )

        mock_dependencies[
            "multi_source_service"
        ].compare_deployed_versions.return_value = {
            "version_upgrades": ["existing"],
            "source_changes": [],
            "needs_update": ["existing"],
            "new_agents": [],
        }

        templates, sources, cleanup = service._get_multi_source_templates(
            excluded_agents=[],
            config=Mock(),
            agents_dir=agents_dir,
            force_rebuild=False,
        )

        assert len(templates) == 1
        mock_dependencies[
            "multi_source_service"
        ].compare_deployed_versions.assert_called_once()

    def test_get_multi_source_templates_force_rebuild(
        self, service, tmp_path, mock_dependencies
    ):
        """Test multi-source templates with force rebuild."""
        agents_dir = tmp_path / ".claude" / "agents"

        mock_dependencies[
            "multi_source_service"
        ].get_agents_for_deployment.return_value = (
            {
                "agent1": tmp_path / "templates" / "agent1.json",
                "agent2": tmp_path / "templates" / "agent2.json",
            },
            {"agent1": "system", "agent2": "project"},
            {"removed": []},
        )

        templates, sources, cleanup = service._get_multi_source_templates(
            excluded_agents=[], config=Mock(), agents_dir=agents_dir, force_rebuild=True
        )

        # With force_rebuild, all agents should be included
        assert len(templates) == 2
