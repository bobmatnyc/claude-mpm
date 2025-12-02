"""Tests for AgentSelectionService.

Tests agent selection modes:
- Minimal configuration (6 core agents)
- Auto-configure (toolchain-based selection)
- Agent validation
- Error handling
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from src.claude_mpm.services.agents.agent_selection_service import AgentSelectionService


class TestMinimalConfiguration:
    """Test minimal configuration deployment mode."""

    def test_deploy_minimal_configuration_success(self):
        """Test deploying minimal configuration successfully."""
        # Mock deployment service
        mock_deployment = Mock()
        mock_deployment.list_available_agents.return_value = [
            {"agent_id": "engineer", "name": "Engineer"},
            {"agent_id": "documentation", "name": "Documentation"},
            {"agent_id": "qa", "name": "QA"},
            {"agent_id": "research", "name": "Research"},
            {"agent_id": "ops", "name": "Ops"},
            {"agent_id": "ticketing", "name": "Ticketing"},
        ]

        mock_deployment.deploy_agent.return_value = {
            "deployed": True,
            "agent_name": "engineer",
            "source": "test-repo",
            "priority": 100,
        }

        service = AgentSelectionService(mock_deployment)
        result = service.deploy_minimal_configuration()

        assert result["status"] == "success"
        assert result["mode"] == "minimal"
        assert result["deployed_count"] == 6
        assert result["failed_count"] == 0
        assert result["missing_count"] == 0
        assert len(result["deployed_agents"]) == 6

        # Verify all minimal agents deployed
        for agent in AgentSelectionService.MINIMAL_AGENTS:
            assert agent in result["deployed_agents"]

    def test_deploy_minimal_configuration_dry_run(self):
        """Test minimal configuration in dry-run mode."""
        mock_deployment = Mock()
        mock_deployment.list_available_agents.return_value = [
            {"agent_id": agent, "name": agent.title()}
            for agent in AgentSelectionService.MINIMAL_AGENTS
        ]

        mock_deployment.deploy_agent.return_value = {
            "deployed": False,
            "dry_run": True,
            "agent_name": "engineer",
        }

        service = AgentSelectionService(mock_deployment)
        result = service.deploy_minimal_configuration(dry_run=True)

        assert result["dry_run"] is True
        # In dry run, agents are counted as "deployed" because they would be deployed
        assert result["deployed_count"] == 6
        assert result["status"] == "success"

    def test_deploy_minimal_configuration_missing_agents(self):
        """Test minimal configuration with some agents missing."""
        mock_deployment = Mock()
        # Only 4 out of 6 agents available
        mock_deployment.list_available_agents.return_value = [
            {"agent_id": "engineer", "name": "Engineer"},
            {"agent_id": "qa", "name": "QA"},
            {"agent_id": "research", "name": "Research"},
            {"agent_id": "ops", "name": "Ops"},
        ]

        mock_deployment.deploy_agent.return_value = {
            "deployed": True,
            "agent_name": "engineer",
        }

        service = AgentSelectionService(mock_deployment)
        result = service.deploy_minimal_configuration()

        assert result["status"] == "partial"
        assert result["deployed_count"] == 4
        assert result["missing_count"] == 2
        assert "documentation" in result["missing_agents"]
        assert "ticketing" in result["missing_agents"]

    def test_deploy_minimal_configuration_deployment_failure(self):
        """Test minimal configuration with deployment failures."""
        mock_deployment = Mock()
        mock_deployment.list_available_agents.return_value = [
            {"agent_id": agent, "name": agent.title()}
            for agent in AgentSelectionService.MINIMAL_AGENTS
        ]

        # Simulate some deployments failing
        def deploy_side_effect(agent_name, dry_run=False):
            if agent_name in ["engineer", "qa"]:
                return {"deployed": True, "agent_name": agent_name}
            return {
                "deployed": False,
                "agent_name": agent_name,
                "error": "Deployment failed",
            }

        mock_deployment.deploy_agent.side_effect = deploy_side_effect

        service = AgentSelectionService(mock_deployment)
        result = service.deploy_minimal_configuration()

        assert result["status"] == "partial"
        assert result["deployed_count"] == 2
        assert result["failed_count"] == 4
        assert "engineer" in result["deployed_agents"]
        assert "qa" in result["deployed_agents"]
        assert len(result["failed_agents"]) == 4


class TestAutoConfiguration:
    """Test auto-configure deployment mode."""

    def test_deploy_auto_configure_python_project(self, tmp_path: Path):
        """Test auto-configure for Python project."""
        # Create Python project
        (tmp_path / "main.py").touch()
        (tmp_path / "pyproject.toml").touch()

        # Mock deployment service
        mock_deployment = Mock()
        mock_deployment.list_available_agents.return_value = [
            {"agent_id": "python-engineer", "name": "Python Engineer"},
            {"agent_id": "qa", "name": "QA"},
            {"agent_id": "research", "name": "Research"},
            {"agent_id": "documentation", "name": "Documentation"},
            {"agent_id": "ticketing", "name": "Ticketing"},
        ]

        mock_deployment.deploy_agent.return_value = {
            "deployed": True,
            "agent_name": "python-engineer",
        }

        service = AgentSelectionService(mock_deployment)
        result = service.deploy_auto_configure(project_path=tmp_path)

        assert result["status"] in ["success", "partial"]
        assert result["mode"] == "auto_configure"
        assert "python" in result["toolchain"]["languages"]
        assert "python-engineer" in result["recommended_agents"]
        # Core agents should be included
        for core_agent in ["qa", "research", "documentation", "ticketing"]:
            assert core_agent in result["recommended_agents"]

    def test_deploy_auto_configure_javascript_react(self, tmp_path: Path):
        """Test auto-configure for JavaScript/React project."""
        # Create React project
        (tmp_path / "App.jsx").touch()
        (tmp_path / "package.json").write_text(
            """
{
  "dependencies": {
    "react": "^18.0.0"
  }
}
"""
        )

        mock_deployment = Mock()
        mock_deployment.list_available_agents.return_value = [
            {"agent_id": "react-engineer", "name": "React Engineer"},
            {"agent_id": "qa", "name": "QA"},
            {"agent_id": "research", "name": "Research"},
            {"agent_id": "documentation", "name": "Documentation"},
            {"agent_id": "ticketing", "name": "Ticketing"},
        ]

        mock_deployment.deploy_agent.return_value = {
            "deployed": True,
            "agent_name": "react-engineer",
        }

        service = AgentSelectionService(mock_deployment)
        result = service.deploy_auto_configure(project_path=tmp_path)

        assert result["status"] in ["success", "partial"]
        assert "javascript" in result["toolchain"]["languages"]
        assert "react" in result["toolchain"]["frameworks"]
        assert "react-engineer" in result["recommended_agents"]

    def test_deploy_auto_configure_multi_language(self, tmp_path: Path):
        """Test auto-configure for multi-language project."""
        # Create multi-language project
        (tmp_path / "backend.py").touch()
        (tmp_path / "frontend.js").touch()
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "package.json").touch()

        mock_deployment = Mock()
        mock_deployment.list_available_agents.return_value = [
            {"agent_id": "python-engineer", "name": "Python Engineer"},
            {"agent_id": "javascript-engineer-agent", "name": "JavaScript Engineer"},
            {"agent_id": "qa", "name": "QA"},
            {"agent_id": "research", "name": "Research"},
            {"agent_id": "documentation", "name": "Documentation"},
            {"agent_id": "ticketing", "name": "Ticketing"},
        ]

        mock_deployment.deploy_agent.return_value = {
            "deployed": True,
            "agent_name": "test",
        }

        service = AgentSelectionService(mock_deployment)
        result = service.deploy_auto_configure(project_path=tmp_path)

        assert "python" in result["toolchain"]["languages"]
        assert "javascript" in result["toolchain"]["languages"]
        assert "python-engineer" in result["recommended_agents"]
        assert "javascript-engineer-agent" in result["recommended_agents"]

    def test_deploy_auto_configure_invalid_path(self):
        """Test auto-configure with invalid project path."""
        mock_deployment = Mock()
        service = AgentSelectionService(mock_deployment)

        result = service.deploy_auto_configure(project_path=Path("/nonexistent/path"))

        assert result["status"] == "error"
        assert "error" in result
        assert result["deployed_count"] == 0

    def test_deploy_auto_configure_dry_run(self, tmp_path: Path):
        """Test auto-configure in dry-run mode."""
        (tmp_path / "main.py").touch()

        mock_deployment = Mock()
        mock_deployment.list_available_agents.return_value = [
            {"agent_id": "python-engineer", "name": "Python Engineer"},
            {"agent_id": "qa", "name": "QA"},
            {"agent_id": "research", "name": "Research"},
            {"agent_id": "documentation", "name": "Documentation"},
            {"agent_id": "ticketing", "name": "Ticketing"},
        ]

        mock_deployment.deploy_agent.return_value = {
            "deployed": False,
            "dry_run": True,
            "agent_name": "test",
        }

        service = AgentSelectionService(mock_deployment)
        result = service.deploy_auto_configure(project_path=tmp_path, dry_run=True)

        assert result["dry_run"] is True
        # In dry run, agents are counted as deployed (would be deployed)
        assert result["deployed_count"] == 5  # python-engineer + 4 core agents
        assert result["status"] == "success"

    def test_deploy_auto_configure_no_toolchain_detected(self, tmp_path: Path):
        """Test auto-configure with no toolchain detected."""
        # Empty project
        mock_deployment = Mock()
        mock_deployment.list_available_agents.return_value = [
            {"agent_id": "engineer", "name": "Engineer"},
            {"agent_id": "qa", "name": "QA"},
            {"agent_id": "research", "name": "Research"},
            {"agent_id": "documentation", "name": "Documentation"},
            {"agent_id": "ticketing", "name": "Ticketing"},
        ]

        mock_deployment.deploy_agent.return_value = {
            "deployed": True,
            "agent_name": "test",
        }

        service = AgentSelectionService(mock_deployment)
        result = service.deploy_auto_configure(project_path=tmp_path)

        # Should fall back to generic engineer
        assert "engineer" in result["recommended_agents"]
        # Core agents should still be included
        assert "qa" in result["recommended_agents"]


class TestAgentValidation:
    """Test agent availability validation."""

    def test_validate_agent_availability_all_available(self):
        """Test validation when all agents are available."""
        mock_deployment = Mock()
        service = AgentSelectionService(mock_deployment)

        required = ["engineer", "qa", "research"]
        available = {"engineer", "qa", "research", "documentation"}

        available_list, missing_list = service._validate_agent_availability(
            required, available
        )

        assert len(available_list) == 3
        assert len(missing_list) == 0
        assert "engineer" in available_list
        assert "qa" in available_list
        assert "research" in available_list

    def test_validate_agent_availability_some_missing(self):
        """Test validation when some agents are missing."""
        mock_deployment = Mock()
        service = AgentSelectionService(mock_deployment)

        required = ["engineer", "qa", "research", "special-agent"]
        available = {"engineer", "qa", "research"}

        available_list, missing_list = service._validate_agent_availability(
            required, available
        )

        assert len(available_list) == 3
        assert len(missing_list) == 1
        assert "special-agent" in missing_list

    def test_validate_agent_availability_all_missing(self):
        """Test validation when all agents are missing."""
        mock_deployment = Mock()
        service = AgentSelectionService(mock_deployment)

        required = ["agent1", "agent2", "agent3"]
        available = {"other1", "other2"}

        available_list, missing_list = service._validate_agent_availability(
            required, available
        )

        assert len(available_list) == 0
        assert len(missing_list) == 3


class TestSelectionModes:
    """Test selection mode metadata."""

    def test_get_available_selection_modes(self):
        """Test retrieving available selection modes."""
        mock_deployment = Mock()
        service = AgentSelectionService(mock_deployment)

        modes = service.get_available_selection_modes()

        assert len(modes) == 2

        # Minimal mode
        minimal_mode = next(m for m in modes if m["mode"] == "minimal")
        assert minimal_mode["agent_count"] == 6
        assert "agents" in minimal_mode
        assert len(minimal_mode["agents"]) == 6

        # Auto-configure mode
        auto_mode = next(m for m in modes if m["mode"] == "auto_configure")
        assert auto_mode["agent_count"] == "varies"
        assert auto_mode["requires_project_scan"] is True
        assert "toolchain_support" in auto_mode


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_workflow_minimal_to_auto(self, tmp_path: Path):
        """Test workflow from minimal to auto-configure."""
        # Create Python project
        (tmp_path / "main.py").touch()
        (tmp_path / "pyproject.toml").write_text(
            """
[tool.poetry.dependencies]
python = "^3.9"
fastapi = "^0.95.0"
"""
        )

        # Mock deployment service
        mock_deployment = Mock()
        mock_deployment.list_available_agents.return_value = [
            {"agent_id": "engineer", "name": "Engineer"},
            {"agent_id": "python-engineer", "name": "Python Engineer"},
            {"agent_id": "qa", "name": "QA"},
            {"agent_id": "research", "name": "Research"},
            {"agent_id": "documentation", "name": "Documentation"},
            {"agent_id": "ticketing", "name": "Ticketing"},
            {"agent_id": "ops", "name": "Ops"},
        ]

        mock_deployment.deploy_agent.return_value = {
            "deployed": True,
            "agent_name": "test",
        }

        service = AgentSelectionService(mock_deployment)

        # First: Deploy minimal configuration
        minimal_result = service.deploy_minimal_configuration()
        assert minimal_result["status"] == "success"
        assert minimal_result["deployed_count"] == 6

        # Then: Deploy auto-configure (should detect Python + FastAPI)
        auto_result = service.deploy_auto_configure(project_path=tmp_path)
        assert auto_result["status"] in ["success", "partial"]
        assert "python" in auto_result["toolchain"]["languages"]
        assert "fastapi" in auto_result["toolchain"]["frameworks"]
        assert "python-engineer" in auto_result["recommended_agents"]

    def test_error_handling_deployment_failure(self):
        """Test error handling when deployment fails."""
        mock_deployment = Mock()
        mock_deployment.list_available_agents.return_value = []
        mock_deployment.deploy_agent.side_effect = Exception("Deployment error")

        service = AgentSelectionService(mock_deployment)
        result = service.deploy_minimal_configuration()

        # Should handle error gracefully
        assert result["status"] in ["error", "partial"]
        assert result["failed_count"] >= 0

    def test_repr_method(self):
        """Test __repr__ method."""
        mock_deployment = Mock()
        mock_deployment.__repr__ = Mock(return_value="MockDeployment")

        service = AgentSelectionService(mock_deployment)
        repr_str = repr(service)

        assert "AgentSelectionService" in repr_str
        assert "deployment_service=" in repr_str
