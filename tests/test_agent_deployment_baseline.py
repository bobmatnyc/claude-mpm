#!/usr/bin/env python3
"""
Baseline Test Coverage for AgentDeploymentService
================================================

This test suite establishes comprehensive baseline coverage for the
AgentDeploymentService before refactoring. It tests all major methods
and functionality to ensure we don't break anything during refactoring.

Coverage Goals:
- All public methods tested
- All major code paths covered
- Edge cases and error conditions tested
- Integration points verified
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)


class TestAgentDeploymentServiceBaseline:
    """Baseline test coverage for AgentDeploymentService."""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            templates_dir = temp_path / "templates"
            agents_dir = temp_path / "agents"
            working_dir = temp_path / "working"

            templates_dir.mkdir()
            agents_dir.mkdir()
            working_dir.mkdir()

            yield {
                "temp": temp_path,
                "templates": templates_dir,
                "agents": agents_dir,
                "working": working_dir,
            }

    @pytest.fixture
    def sample_template(self, temp_dirs):
        """Create a sample agent template."""
        template_content = {
            "name": "test-agent",
            "description": "Test agent for baseline coverage",
            "model": "sonnet",
            "tools": ["Read", "Write"],
            "capabilities": {"tools": ["Read", "Write"], "model": "sonnet"},
            "when_to_use": ["Testing", "Validation"],
            "specialized_knowledge": ["Testing frameworks"],
            "unique_capabilities": ["Test execution"],
        }

        template_file = temp_dirs["templates"] / "test_agent.json"
        template_file.write_text(json.dumps(template_content, indent=2))
        return template_file

    @pytest.fixture
    def base_agent_content(self):
        """Sample base agent content."""
        return """# Base Agent Instructions

This is the base agent configuration that all agents inherit.

## Core Capabilities
- File operations
- Code analysis
- Documentation

## Instructions
Follow these guidelines for all tasks.
"""

    @pytest.fixture
    def base_agent_file(self, temp_dirs, base_agent_content):
        """Create base agent file."""
        base_file = temp_dirs["templates"] / "base_agent.md"
        base_file.write_text(base_agent_content)
        return base_file

    @pytest.fixture
    def deployment_service(self, temp_dirs, base_agent_file):
        """Create AgentDeploymentService instance."""
        return AgentDeploymentService(
            templates_dir=temp_dirs["templates"],
            base_agent_path=base_agent_file,
            working_directory=temp_dirs["working"],
        )

    def test_initialization(self, deployment_service, temp_dirs):
        """Test service initialization."""
        assert deployment_service.templates_dir == temp_dirs["templates"]
        assert deployment_service.working_directory == temp_dirs["working"]
        assert hasattr(deployment_service, "logger")
        assert hasattr(deployment_service, "metrics_collector")
        assert hasattr(deployment_service, "template_builder")
        assert hasattr(deployment_service, "version_manager")
        assert hasattr(deployment_service, "environment_manager")
        assert hasattr(deployment_service, "validator")
        assert hasattr(deployment_service, "filesystem_manager")

    def test_deploy_agents_basic(self, deployment_service, sample_template, temp_dirs):
        """Test basic agent deployment."""
        result = deployment_service.deploy_agents(
            target_dir=temp_dirs["agents"], force_rebuild=True
        )

        assert isinstance(result, dict)
        assert "deployed" in result
        assert "errors" in result
        assert "total" in result
        assert "target_dir" in result

    def test_list_available_agents(self, deployment_service, sample_template):
        """Test listing available agents."""
        agents = deployment_service.list_available_agents()
        assert isinstance(agents, list)
        assert len(agents) >= 1

        # Check agent structure
        agent = agents[0]
        assert "name" in agent
        assert "description" in agent
        assert "path" in agent  # Actual field name is 'path', not 'template_path'

    def test_deploy_single_agent(self, deployment_service, sample_template, temp_dirs):
        """Test deploying a single agent."""
        result = deployment_service.deploy_agent(
            agent_name="test_agent", target_dir=temp_dirs["agents"], force_rebuild=True
        )
        assert isinstance(result, bool)

    def test_set_claude_environment(self, deployment_service, temp_dirs):
        """Test setting Claude environment variables."""
        env_vars = deployment_service.set_claude_environment(
            config_dir=temp_dirs["working"] / ".claude"
        )

        assert isinstance(env_vars, dict)
        assert len(env_vars) > 0
        # Should set environment variables
        for key, _value in env_vars.items():
            assert key in [
                "CLAUDE_CONFIG_DIR",
                "CLAUDE_MAX_PARALLEL_SUBAGENTS",
                "CLAUDE_TIMEOUT",
            ]

    def test_verify_deployment(self, deployment_service, temp_dirs):
        """Test deployment verification."""
        result = deployment_service.verify_deployment(
            config_dir=temp_dirs["working"] / ".claude"
        )

        assert isinstance(result, dict)
        # Actual fields from verify_deployment
        assert "agents_found" in result
        assert "config_dir" in result

    def test_get_deployment_metrics(self, deployment_service):
        """Test getting deployment metrics."""
        metrics = deployment_service.get_deployment_metrics()

        assert isinstance(metrics, dict)
        assert "total_deployments" in metrics
        assert "average_deployment_time_ms" in metrics  # Actual field name
        assert "successful_deployments" in metrics  # Actual field name

    def test_reset_metrics(self, deployment_service):
        """Test resetting deployment metrics."""
        # Get initial metrics
        deployment_service.get_deployment_metrics()

        # Reset metrics
        deployment_service.reset_metrics()

        # Verify reset
        reset_metrics = deployment_service.get_deployment_metrics()
        assert reset_metrics["total_deployments"] == 0

    def test_clean_deployment(self, deployment_service, temp_dirs):
        """Test cleaning deployment."""
        result = deployment_service.clean_deployment(
            config_dir=temp_dirs["working"] / ".claude"
        )

        assert isinstance(result, dict)
        assert "removed" in result
        # 'preserved' field may not exist if no agents directory found

    def test_validate_agent(self, deployment_service, sample_template):
        """Test agent validation."""
        is_valid, errors = deployment_service.validate_agent(sample_template)

        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_get_deployment_status(self, deployment_service):
        """Test getting deployment status."""
        status = deployment_service.get_deployment_status()

        assert isinstance(status, dict)
        assert "deployment_metrics" in status  # Actual field name

    def test_error_handling_invalid_template(self, deployment_service, temp_dirs):
        """Test error handling with invalid template."""
        # Create invalid template
        invalid_template = temp_dirs["templates"] / "invalid.json"
        invalid_template.write_text("{ invalid json")

        result = deployment_service.deploy_agents(
            target_dir=temp_dirs["agents"], force_rebuild=True
        )

        # Should handle error gracefully
        assert "errors" in result

    def test_version_parsing(self, deployment_service):
        """Test version parsing functionality via version manager."""
        # Test various version formats
        version_tests = [
            ("1.0.0", (1, 0, 0)),
            ("v2.1.3", (2, 1, 3)),
            ("3", (0, 3, 0)),  # Old format
            ("invalid", (0, 0, 0)),  # Invalid format
        ]

        for version_str, expected in version_tests:
            result = deployment_service.version_manager.parse_version(version_str)
            assert result == expected

    def test_format_version_display(self, deployment_service):
        """Test version display formatting via version manager."""
        version_tuple = (1, 2, 3)
        formatted = deployment_service.version_manager.format_version_display(
            version_tuple
        )
        assert formatted == "1.2.3"

    def test_yaml_list_formatting(self, deployment_service):
        """Test YAML list formatting via template builder."""
        items = ["item1", "item2", "item3"]
        formatted = deployment_service.template_builder.format_yaml_list(items, 2)
        assert isinstance(formatted, str)
        assert "item1" in formatted
        assert "item2" in formatted
        assert "item3" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
