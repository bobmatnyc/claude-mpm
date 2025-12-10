"""Test validation, repair, and results management operations.

This module tests agent validation, frontmatter repair, deployment verification,
and results recording for deployment operations.
"""

from unittest.mock import Mock, patch

from conftest import TestAgentDeploymentService


class TestValidationAndResults(TestAgentDeploymentService):
    """Test validation, repair, and results management operations."""

    def test_repair_existing_agents(self, service, tmp_path):
        """Test repairing existing agents with broken frontmatter."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Create agent with broken frontmatter
        broken_agent = agents_dir / "broken.md"
        broken_agent.write_text("name: broken\n---\nContent")

        results = {"repaired": [], "errors": []}

        with patch.object(
            service, "_validate_and_repair_existing_agents"
        ) as mock_repair:
            mock_repair.return_value = {"repaired": ["broken"]}

            service._repair_existing_agents(agents_dir, results)

        assert results["repaired"] == ["broken"]

    def test_validate_and_repair_existing_agents(self, service, tmp_path):
        """Test validation and repair of existing agents."""
        agents_dir = tmp_path / ".claude" / "agents"

        with patch(
            "claude_mpm.services.agents.deployment.agent_frontmatter_validator.AgentFrontmatterValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_and_repair_existing_agents.return_value = {
                "repaired": ["agent1", "agent2"],
                "errors": [],
            }
            mock_validator_class.return_value = mock_validator

            result = service._validate_and_repair_existing_agents(agents_dir)

        assert result["repaired"] == ["agent1", "agent2"]

    def test_verify_deployment(self, service, tmp_path, mock_dependencies):
        """Test deployment verification."""
        config_dir = tmp_path / ".claude"
        expected_result = {"status": "success", "agents_found": 5, "errors": []}

        mock_dependencies["validator"].verify_deployment.return_value = expected_result

        result = service.verify_deployment(config_dir)

        assert result == expected_result
        mock_dependencies["validator"].verify_deployment.assert_called_with(config_dir)

    def test_validate_agent_valid(self, service, tmp_path):
        """Test validating a valid agent configuration."""
        agent_path = tmp_path / "agent.md"
        agent_path.write_text(
            """---
name: test_agent
version: 1.0.0
description: Test agent
tools:
  - tool1
  - tool2
---
Agent content"""
        )

        is_valid, errors = service.validate_agent(agent_path)

        assert is_valid is True
        assert errors == []

    def test_validate_agent_missing_frontmatter(self, service, tmp_path):
        """Test validating agent with missing frontmatter."""
        agent_path = tmp_path / "agent.md"
        agent_path.write_text("Agent content without frontmatter")

        is_valid, errors = service.validate_agent(agent_path)

        assert is_valid is False
        assert "Missing YAML frontmatter" in errors[0]

    def test_validate_agent_missing_fields(self, service, tmp_path):
        """Test validating agent with missing required fields."""
        agent_path = tmp_path / "agent.md"
        agent_path.write_text(
            """---
name: test_agent
---
Agent content"""
        )

        is_valid, errors = service.validate_agent(agent_path)

        assert is_valid is False
        assert any("version" in error for error in errors)
        assert any("description" in error for error in errors)

    def test_initialize_deployment_results(self, service, tmp_path):
        """Test initializing deployment results."""
        agents_dir = tmp_path / ".claude" / "agents"
        start_time = 1234567890.0

        results = service.results_manager.initialize_deployment_results(
            agents_dir, start_time
        )

        assert results["target_dir"] == str(agents_dir)
        assert results["deployed"] == []
        assert results["updated"] == []
        assert results["migrated"] == []
        assert results["skipped"] == []
        assert results["errors"] == []
        assert results["metrics"]["start_time"] == start_time

    def test_record_agent_deployment_new(self, service, tmp_path):
        """Test recording a new agent deployment."""
        results = service.results_manager.initialize_deployment_results(tmp_path, 0)

        service.results_manager.record_agent_deployment(
            agent_name="new_agent",
            template_file=tmp_path / "new_agent.json",
            target_file=tmp_path / "new_agent.md",
            is_update=False,
            is_migration=False,
            reason="new deployment",
            agent_start_time=0,
            results=results,
        )

        assert len(results["deployed"]) == 1
        assert results["deployed"][0]["name"] == "new_agent"

    def test_record_agent_deployment_update(self, service, tmp_path):
        """Test recording an agent update."""
        results = service.results_manager.initialize_deployment_results(tmp_path, 0)

        service.results_manager.record_agent_deployment(
            agent_name="updated_agent",
            template_file=tmp_path / "updated_agent.json",
            target_file=tmp_path / "updated_agent.md",
            is_update=True,
            is_migration=False,
            reason="version update",
            agent_start_time=0,
            results=results,
        )

        assert len(results["updated"]) == 1
        assert results["updated"][0]["name"] == "updated_agent"

    def test_record_agent_deployment_migration(self, service, tmp_path):
        """Test recording an agent migration."""
        results = service.results_manager.initialize_deployment_results(tmp_path, 0)

        service.results_manager.record_agent_deployment(
            agent_name="migrated_agent",
            template_file=tmp_path / "migrated_agent.json",
            target_file=tmp_path / "migrated_agent.md",
            is_update=True,
            is_migration=True,
            reason="migration from serial to semantic",
            agent_start_time=0,
            results=results,
        )

        assert len(results["migrated"]) == 1
        assert results["migrated"][0]["name"] == "migrated_agent"
        assert "migration" in results["migrated"][0]["reason"]

    def test_get_deployment_metrics(self, service, mock_dependencies):
        """Test getting deployment metrics."""
        # The service.get_deployment_metrics() calls results_manager.get_deployment_metrics()
        # which returns the internal _deployment_metrics dict
        result = service.get_deployment_metrics()

        # Check that the result has the expected structure (initialized to 0)
        assert "total_deployments" in result
        assert "successful_deployments" in result
        assert "failed_deployments" in result
        assert result["total_deployments"] == 0  # Fresh instance starts at 0

    def test_get_deployment_status(self, service, mock_dependencies):
        """Test getting deployment status."""
        expected_status = {
            "status": "healthy",
            "last_deployment": "2024-01-01T00:00:00Z",
            "agents_deployed": 25,
        }

        mock_dependencies[
            "metrics_collector"
        ].get_deployment_status.return_value = expected_status

        result = service.get_deployment_status()

        assert result == expected_status

    def test_reset_metrics(self, service, mock_dependencies):
        """Test resetting deployment metrics."""
        # First, update some metrics
        service.results_manager.update_deployment_metrics(True)

        # Verify metrics were updated
        metrics = service.get_deployment_metrics()
        assert metrics["total_deployments"] == 1

        # Now reset
        service.reset_metrics()

        # Verify metrics were reset
        metrics = service.get_deployment_metrics()
        assert metrics["total_deployments"] == 0
