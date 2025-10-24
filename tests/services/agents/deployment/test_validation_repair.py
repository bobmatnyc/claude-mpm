"""Unit tests for Validation and Repair Operations.

Tests validation, repair, and results management functionality.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.core.config import Config
from claude_mpm.core.exceptions import AgentDeploymentError
from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)


class TestAgentDeploymentService:
    """Test suite for AgentDeploymentService."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock(spec=Config)
        config.get = Mock(return_value=None)
        config.agent = Mock()
        config.agent.excluded_agents = []
        config.agent.exclude_agents = []
        config.agent.case_sensitive = False
        config.agent.exclude_dependencies = False
        return config

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock instances of all helper services."""
        return {
            "template_builder": Mock(),
            "version_manager": Mock(),
            "metrics_collector": Mock(),
            "environment_manager": Mock(),
            "validator": Mock(),
            "filesystem_manager": Mock(),
            "discovery_service": Mock(),
            "multi_source_service": Mock(),
            "configuration_manager": Mock(),
            "format_converter": Mock(),
        }

    @pytest.fixture
    def service(self, tmp_path, mock_config, mock_dependencies):
        """Create an AgentDeploymentService instance with mocked dependencies."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        base_agent_path = tmp_path / "base_agent.json"
        base_agent_data = {
            "name": "base_agent",
            "version": "1.0.0",
            "base_version": "1.0.0",
        }
        base_agent_path.write_text(json.dumps(base_agent_data))

        working_dir = tmp_path / "working"
        working_dir.mkdir(parents=True, exist_ok=True)

        # Patch the service's dependencies
        with patch.multiple(
            "claude_mpm.services.agents.deployment.agent_deployment",
            AgentTemplateBuilder=Mock(
                return_value=mock_dependencies["template_builder"]
            ),
            AgentVersionManager=Mock(return_value=mock_dependencies["version_manager"]),
            AgentMetricsCollector=Mock(
                return_value=mock_dependencies["metrics_collector"]
            ),
            AgentEnvironmentManager=Mock(
                return_value=mock_dependencies["environment_manager"]
            ),
            AgentValidator=Mock(return_value=mock_dependencies["validator"]),
            AgentFileSystemManager=Mock(
                return_value=mock_dependencies["filesystem_manager"]
            ),
            AgentDiscoveryService=Mock(
                return_value=mock_dependencies["discovery_service"]
            ),
            MultiSourceAgentDeploymentService=Mock(
                return_value=mock_dependencies["multi_source_service"]
            ),
            AgentConfigurationManager=Mock(
                return_value=mock_dependencies["configuration_manager"]
            ),
            AgentFormatConverter=Mock(
                return_value=mock_dependencies["format_converter"]
            ),
        ):
            service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=base_agent_path,
                working_directory=working_dir,
                config=mock_config,
            )

            # Inject mock dependencies - these override the ones created during __init__
            for name, mock_obj in mock_dependencies.items():
                setattr(service, name, mock_obj)

            # Ensure templates_dir and working_directory are set
            service.templates_dir = templates_dir
            service.working_directory = working_dir

            return service

    @pytest.fixture
    def sample_agent_template(self, tmp_path):
        """Create a sample agent template file."""
        template_file = tmp_path / "templates" / "test_agent.json"
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_data = {
            "name": "test_agent",
            "version": "2.0.0",
            "description": "Test agent",
            "tools": ["tool1", "tool2"],
        }
        template_file.write_text(json.dumps(template_data))
        return template_file


class TestValidationAndRepair(TestAgentDeploymentService):
    """Test validation and repair operations."""

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
            "claude_mpm.services.agents.deployment.agent_deployment.AgentFrontmatterValidator"
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


class TestResultsManagement(TestAgentDeploymentService):
    """Test results management operations."""

    def test_initialize_deployment_results(self, service, tmp_path):
        """Test initializing deployment results."""
        agents_dir = tmp_path / ".claude" / "agents"
        start_time = 1234567890.0

        results = service._initialize_deployment_results(agents_dir, start_time)

        assert results["target_dir"] == str(agents_dir)
        assert results["deployed"] == []
        assert results["updated"] == []
        assert results["migrated"] == []
        assert results["skipped"] == []
        assert results["errors"] == []
        assert results["metrics"]["start_time"] == start_time

    def test_record_agent_deployment_new(self, service, tmp_path):
        """Test recording a new agent deployment."""
        results = service._initialize_deployment_results(tmp_path, 0)

        service._record_agent_deployment(
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
        results = service._initialize_deployment_results(tmp_path, 0)

        service._record_agent_deployment(
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
        results = service._initialize_deployment_results(tmp_path, 0)

        service._record_agent_deployment(
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
        expected_metrics = {
            "total_deployments": 10,
            "successful_deployments": 8,
            "failed_deployments": 2,
        }

        mock_dependencies["metrics_collector"].get_deployment_metrics.return_value = (
            expected_metrics
        )

        result = service.get_deployment_metrics()

        assert result == expected_metrics

    def test_get_deployment_status(self, service, mock_dependencies):
        """Test getting deployment status."""
        expected_status = {
            "status": "healthy",
            "last_deployment": "2024-01-01T00:00:00Z",
            "agents_deployed": 25,
        }

        mock_dependencies["metrics_collector"].get_deployment_status.return_value = (
            expected_status
        )

        result = service.get_deployment_status()

        assert result == expected_status

    def test_reset_metrics(self, service, mock_dependencies):
        """Test resetting deployment metrics."""
        service.reset_metrics()

        mock_dependencies["metrics_collector"].reset_metrics.assert_called_once()


