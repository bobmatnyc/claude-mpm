"""Integration tests for the refactored agent deployment service.

These tests verify that all refactored components work together correctly
and that the service maintains compatibility with existing functionality.
"""

import json
import shutil
from pathlib import Path

from claude_mpm.core.interfaces import AgentDeploymentInterface
from claude_mpm.services.agents.deployment.interface_adapter import (
    AgentDeploymentInterfaceAdapter,
)

# Import the refactored components
from claude_mpm.services.agents.deployment.refactored_agent_deployment_service import (
    RefactoredAgentDeploymentService,
)
from claude_mpm.services.agents.deployment.strategies import DeploymentContext


class TestRefactoredServiceIntegration:
    """Integration tests for the refactored deployment service."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.temp_dir = tmp_path
        self.working_dir = Path(self.temp_dir)
        self.templates_dir = self.working_dir / "agents"
        self.templates_dir.mkdir()
        self.base_agent_path = self.working_dir / "base_agent.md"

        # Create base agent file
        self.base_agent_path.write_text(
            """---
name: "Base Agent"
description: "Base agent configuration"
author: "claude-mpm"
version: "1.0.0"
model: "sonnet"
tools: ["Read", "Write"]
---

# Base Agent

This is the base agent configuration.
"""
        )

    def teardown_method(self):
        """Clean up test environment after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_template(self, agent_name: str, agent_type: str = "qa") -> Path:
        """Create a test agent template.

        Args:
            agent_name: Name of the agent
            agent_type: Type of the agent

        Returns:
            Path to the created template file
        """
        template_file = self.templates_dir / f"{agent_name}.json"
        template_data = {
            "schema_version": "1.2.0",
            "agent_id": agent_name,
            "agent_version": "1.0.0",
            "agent_type": agent_type,
            "metadata": {
                "name": f"{agent_name.title()} Agent",
                "description": f"A {agent_type} agent for testing",
                "category": "testing",
                "tags": ["test", agent_type],
            },
            "capabilities": {"model": "sonnet", "tools": ["Read", "Write", "Edit"]},
            "instructions": {
                "system_prompt": f"You are a {agent_type} agent for testing purposes."
            },
        }
        template_file.write_text(json.dumps(template_data, indent=2))
        return template_file

    def test_refactored_service_basic_deployment():
        """Test basic deployment functionality with refactored service."""
        # Create test templates
        self.create_test_template("test-agent", "qa")
        self.create_test_template("dev-agent", "development")

        # Create refactored service
        service = RefactoredAgentDeploymentService(
            templates_dir=self.templates_dir,
            base_agent_path=self.base_agent_path,
            working_directory=self.working_dir,
        )

        # Test deployment (use include_all=True to trigger project mode)
        result = service.deploy_agents(force=False, include_all=True)

        # Verify result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "deployed" in result
        assert "updated" in result
        assert "errors" in result
        assert "metadata" in result

        # Check that agents directory was created
        agents_dir = self.working_dir / ".claude" / "agents"
        assert agents_dir.exists()

        # Verify service status
        status = service.get_deployment_status()
        assert status["service_version"] == "refactored-1.0.0"
        assert status["status"] == "ready"

    def test_interface_adapter_integration():
        """Test interface adapter with actual deployment service."""
        # Create test template
        self.create_test_template("adapter-test", "qa")

        # Create service and adapter
        service = RefactoredAgentDeploymentService(
            templates_dir=self.templates_dir,
            base_agent_path=self.base_agent_path,
            working_directory=self.working_dir,
        )
        adapter = AgentDeploymentInterfaceAdapter(service)

        # Verify interface compliance
        assert isinstance(adapter, AgentDeploymentInterface)

        # Test deployment through adapter
        result = adapter.deploy_agents(force=True, include_all=False)

        # Verify adapter metadata
        assert result["interface_version"] == "1.0.0"
        assert result["adapter_used"] is True

        # Test validation through adapter
        template_file = self.templates_dir / "adapter-test.json"
        is_valid, errors = adapter.validate_agent(template_file)
        assert is_valid is True
        assert len(errors) == 0

        # Test cleanup through adapter
        cleanup_result = adapter.clean_deployment(preserve_user_agents=True)
        assert isinstance(cleanup_result, bool)

    def test_deployment_strategies_integration():
        """Test deployment strategies with actual service."""
        # Create test template
        self.create_test_template("strategy-test", "qa")

        # Test different deployment contexts
        contexts = [
            DeploymentContext(
                templates_dir=self.templates_dir,
                base_agent_path=self.base_agent_path,
                working_directory=self.working_dir,
                target_dir=self.working_dir
                / ".claude"
                / "agents",  # Add target_dir within working_dir
                deployment_mode="update",
            ),
            DeploymentContext(
                templates_dir=self.templates_dir,
                base_agent_path=self.base_agent_path,
                working_directory=self.working_dir,
                deployment_mode="project",
            ),
        ]

        service = RefactoredAgentDeploymentService(
            templates_dir=self.templates_dir,
            base_agent_path=self.base_agent_path,
            working_directory=self.working_dir,
        )

        for context in contexts:
            # Test strategy selection
            strategy = service.strategy_selector.select_strategy(context)
            assert strategy is not None

            # Test target directory determination
            target_dir = strategy.determine_target_directory(context)
            assert isinstance(target_dir, Path)

    def test_validation_integration():
        """Test validation components with actual files."""
        # Create test template and agent files
        template_file = self.create_test_template("validation-test", "qa")

        # Create an agent file
        agents_dir = self.working_dir / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        agent_file = agents_dir / "validation-test.md"
        agent_file.write_text(
            """---
name: "Validation Test Agent"
description: "Agent for validation testing"
author: "claude-mpm"
version: "1.0.0"
model: "sonnet"
tools: ["Read", "Write"]
---

# Validation Test Agent

This agent is for validation testing.
"""
        )

        service = RefactoredAgentDeploymentService(
            templates_dir=self.templates_dir,
            base_agent_path=self.base_agent_path,
            working_directory=self.working_dir,
        )

        # Test template validation
        is_valid, errors = service.validate_agent(template_file)
        assert is_valid is True
        assert len(errors) == 0

        # Test agent file validation
        is_valid, errors = service.validate_agent(agent_file)
        assert is_valid is True
        assert len(errors) == 0

        # Test validation of non-existent file
        is_valid, errors = service.validate_agent(Path("/nonexistent/file.md"))
        assert is_valid is False
        assert len(errors) > 0

    def test_facade_integration():
        """Test deployment facade integration."""
        # Create test template
        self.create_test_template("facade-test", "qa")

        service = RefactoredAgentDeploymentService(
            templates_dir=self.templates_dir,
            base_agent_path=self.base_agent_path,
            working_directory=self.working_dir,
        )

        # Test facade functionality
        facade = service.deployment_facade

        # Test available executors
        executors = facade.get_available_executors()
        assert len(executors) >= 1  # At least sync should be available

        # Test executor recommendations
        recommendation = facade.get_recommended_executor(agent_count=2)
        assert recommendation in ["sync", "async"]

        # Test direct facade deployment
        result = facade.deploy_agents(
            templates_dir=self.templates_dir,
            base_agent_path=self.base_agent_path,
            working_directory=self.working_dir,
            force_rebuild=True,
            use_async=False,
        )

        assert isinstance(result, dict)
        assert "metadata" in result
        assert "facade_version" in result["metadata"]

    def test_error_handling_integration():
        """Test error handling across components."""
        # Create service with invalid paths to test error handling
        service = RefactoredAgentDeploymentService(
            templates_dir=Path("/nonexistent/templates"),
            base_agent_path=Path("/nonexistent/base_agent.md"),
            working_directory=self.working_dir,
        )

        # Test deployment with invalid paths
        result = service.deploy_agents(force=False, include_all=False)

        # Should handle errors gracefully
        assert isinstance(result, dict)
        assert "success" in result
        assert "errors" in result

        # Test validation with invalid file
        is_valid, errors = service.validate_agent(Path("/invalid/path.md"))
        assert is_valid is False
        assert len(errors) > 0

        # Test status retrieval (should work even with invalid paths)
        status = service.get_deployment_status()
        assert isinstance(status, dict)
        assert "service_version" in status

    def test_metrics_collection_integration():
        """Test metrics collection across deployment."""
        # Create multiple test templates
        self.create_test_template("metrics-test-1", "qa")
        self.create_test_template("metrics-test-2", "development")
        self.create_test_template("metrics-test-3", "documentation")

        service = RefactoredAgentDeploymentService(
            templates_dir=self.templates_dir,
            base_agent_path=self.base_agent_path,
            working_directory=self.working_dir,
        )

        # Deploy agents
        result = service.deploy_agents(force=True, include_all=True)

        # Check metrics in result
        assert "metrics" in result
        metrics = result["metrics"]

        # Verify metrics structure
        assert isinstance(metrics, dict)

        # Check deployment status for metrics
        status = service.get_deployment_status()
        assert "metrics" in status

        # Verify metrics are being collected
        status_metrics = status["metrics"]
        assert isinstance(status_metrics, dict)
