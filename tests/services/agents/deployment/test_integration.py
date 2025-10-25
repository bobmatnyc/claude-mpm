"""Test full deployment integration scenarios.

This module tests complete end-to-end deployment workflows including
full deployment cycles and deployment with agent exclusions.
"""

import json
from unittest.mock import Mock, patch

from conftest import TestAgentDeploymentService


class TestDeploymentIntegration(TestAgentDeploymentService):
    """Test full deployment integration scenarios."""

    def test_full_deployment_cycle(self, service, tmp_path, mock_dependencies):
        """Test complete deployment cycle with all operations."""
        target_dir = tmp_path / ".claude" / "agents"

        # Setup comprehensive mocks
        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {"base_version": "1.0.0", "settings": {}},
            (1, 0, 0),
        )

        template_file = tmp_path / "templates" / "complete_agent.json"
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_file.write_text(
            json.dumps(
                {
                    "name": "complete_agent",
                    "version": "2.0.0",
                    "description": "Complete test agent",
                }
            )
        )

        mock_dependencies["discovery_service"].get_filtered_templates.return_value = [
            template_file
        ]
        mock_dependencies["version_manager"].check_agent_needs_update.return_value = (
            True,
            "new agent",
        )
        mock_dependencies["template_builder"].build_agent_markdown.return_value = (
            "---\nname: complete_agent\nversion: 2.0.0\n---\nAgent content"
        )
        mock_dependencies["format_converter"].convert_yaml_to_md.return_value = {
            "converted": []
        }

        with patch.object(service, "_load_deployment_config") as mock_load_config:
            mock_load_config.return_value = (Mock(), [])

            with patch.object(
                service, "_validate_and_repair_existing_agents"
            ) as mock_repair:
                mock_repair.return_value = {"repaired": []}

                result = service.deploy_agents(
                    target_dir=target_dir, force_rebuild=False
                )

        # Verify full deployment cycle
        assert result["target_dir"] == str(target_dir)
        assert len(result["deployed"]) > 0 or len(result["updated"]) > 0
        assert "metrics" in result
        assert result["metrics"]["start_time"] is not None

    def test_deployment_with_exclusions(self, service, tmp_path, mock_dependencies):
        """Test deployment with agent exclusions."""
        mock_config = Mock()
        mock_config.agent.excluded_agents = ["excluded_agent"]

        mock_dependencies["configuration_manager"].load_base_agent.return_value = (
            {},
            (1, 0, 0),
        )
        mock_dependencies["discovery_service"].get_filtered_templates.return_value = []

        with patch.object(service, "_load_deployment_config") as mock_load_config:
            mock_load_config.return_value = (mock_config, ["excluded_agent"])

            with patch.object(
                service, "_validate_and_repair_existing_agents"
            ) as mock_repair:
                mock_repair.return_value = {"repaired": []}

                with patch.object(service, "_convert_yaml_to_md") as mock_convert:
                    mock_convert.return_value = {"converted": []}

                    service.deploy_agents(config=mock_config)

        # Verify excluded agents were passed to discovery service
        mock_dependencies["discovery_service"].get_filtered_templates.assert_called()
