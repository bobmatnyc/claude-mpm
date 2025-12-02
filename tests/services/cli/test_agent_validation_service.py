"""
Tests for Agent Validation Service
===================================

WHY: Comprehensive tests ensure the AgentValidationService correctly validates
agent files, fixes issues, and provides detailed reports for the CLI.

DESIGN DECISIONS:
- Test each validation method independently
- Mock dependencies (FrontmatterValidator, AgentRegistry)
- Test error handling and edge cases
- Verify report generation accuracy
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.agents.frontmatter_validator import ValidationResult
from claude_mpm.services.cli.agent_validation_service import (
    AgentValidationService, IAgentValidationService)


class TestAgentValidationService:
    """Test suite for AgentValidationService."""

    @pytest.fixture
    def mock_validator(self):
        """Create a mock FrontmatterValidator."""
        return Mock()

    @pytest.fixture
    def mock_registry(self):
        """Create a mock agent registry."""
        return Mock()

    @pytest.fixture
    def service(self, mock_validator, mock_registry):
        """Create service instance with mocked dependencies."""
        with patch(
            "claude_mpm.services.cli.agent_validation_service.FrontmatterValidator",
            return_value=mock_validator,
        ), patch(
            "claude_mpm.services.cli.agent_validation_service.AgentRegistryAdapter"
        ) as mock_adapter:
            mock_adapter.return_value.registry = mock_registry
            service = AgentValidationService()
            service._registry = (
                mock_registry  # Direct assignment to bypass lazy loading
            )
            service.validator = mock_validator
            return service

    def test_implements_interface(self):
        """Test that service implements IAgentValidationService."""
        service = AgentValidationService()
        assert isinstance(service, IAgentValidationService)

    def test_validate_agent_success(self, service, mock_validator, mock_registry):
        """Test successful validation of a single agent."""
        # Setup mock agent
        mock_agent = Mock()
        mock_agent.path = "/path/to/agent.md"
        mock_registry.get_agent.return_value = mock_agent

        # Setup validation result
        validation_result = ValidationResult(
            is_valid=True, errors=[], warnings=["Minor warning"], corrections=[]
        )
        mock_validator.validate_file.return_value = validation_result

        # Mock file existence
        with patch("pathlib.Path.exists", return_value=True):
            result = service.validate_agent("test-agent")

        assert result["success"] is True
        assert result["agent"] == "test-agent"
        assert result["is_valid"] is True
        assert result["warnings"] == ["Minor warning"]
        assert result["corrections_available"] is False

    def test_validate_agent_not_found(self, service, mock_registry):
        """Test validation when agent is not found."""
        mock_registry.get_agent.return_value = None
        mock_registry.list_agents.return_value = {"agent1": {}, "agent2": {}}

        result = service.validate_agent("nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"]
        assert "agent1" in result["available_agents"]

    def test_validate_agent_file_missing(self, service, mock_registry):
        """Test validation when agent file doesn't exist."""
        mock_agent = Mock()
        mock_agent.path = "/path/to/missing.md"
        mock_registry.get_agent.return_value = mock_agent

        with patch("pathlib.Path.exists", return_value=False):
            result = service.validate_agent("test-agent")

        assert result["success"] is False
        assert result["error"] == "Agent file not found"
        assert result["is_valid"] is False

    def test_validate_all_agents(self, service, mock_validator, mock_registry):
        """Test validation of all agents."""
        # Setup mock agents
        mock_registry.list_agents.return_value = {
            "agent1": {"path": "/path/to/agent1.md"},
            "agent2": {"path": "/path/to/agent2.md"},
            "agent3": {"path": "/path/to/agent3.md"},
        }

        # Setup different validation results
        validation_results = [
            ValidationResult(is_valid=True, errors=[], warnings=[], corrections=[]),
            ValidationResult(
                is_valid=False,
                errors=["Error 1"],
                warnings=["Warning 1"],
                corrections=["Fix 1"],
            ),
            ValidationResult(
                is_valid=True, errors=[], warnings=["Warning 2"], corrections=[]
            ),
        ]
        mock_validator.validate_file.side_effect = validation_results

        with patch("pathlib.Path.exists", return_value=True):
            result = service.validate_all_agents()

        assert result["success"] is True
        assert result["total_agents"] == 3
        assert result["agents_checked"] == 3
        assert result["total_errors"] == 1
        assert result["total_warnings"] == 2
        assert result["total_issues"] == 3
        assert "agent2" in result["agents_with_issues"]

    def test_validate_all_agents_with_missing_files(
        self, service, mock_validator, mock_registry
    ):
        """Test validation when some agent files are missing."""
        mock_registry.list_agents.return_value = {
            "agent1": {"path": "/path/to/agent1.md"},
            "agent2": {"path": "/path/to/missing.md"},
        }

        # Setup validation result for the existing file
        validation_result = ValidationResult(
            is_valid=True, errors=[], warnings=[], corrections=[]
        )
        mock_validator.validate_file.return_value = validation_result

        # First file exists, second doesn't
        exists_side_effect = [True, False]
        with patch("pathlib.Path.exists", side_effect=exists_side_effect):
            result = service.validate_all_agents()

        assert result["success"] is True
        assert result["total_agents"] == 2
        assert result["total_errors"] == 1
        assert (
            len([r for r in result["results"] if r.get("error") == "File not found"])
            == 1
        )

    def test_fix_agent_frontmatter_dry_run(
        self, service, mock_validator, mock_registry
    ):
        """Test fixing agent frontmatter in dry-run mode."""
        mock_agent = Mock()
        mock_agent.path = "/path/to/agent.md"
        mock_registry.get_agent.return_value = mock_agent

        correction_result = ValidationResult(
            is_valid=False,
            errors=["Error to fix"],
            warnings=[],
            corrections=["Fixed error"],
        )
        mock_validator.correct_file.return_value = correction_result

        with patch("pathlib.Path.exists", return_value=True):
            result = service.fix_agent_frontmatter("test-agent", dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["corrections_available"] == ["Fixed error"]
        assert result["corrections_made"] == []
        mock_validator.correct_file.assert_called_once_with(
            Path("/path/to/agent.md"), dry_run=True
        )

    def test_fix_agent_frontmatter_write(self, service, mock_validator, mock_registry):
        """Test fixing agent frontmatter with actual write."""
        mock_agent = Mock()
        mock_agent.path = "/path/to/agent.md"
        mock_registry.get_agent.return_value = mock_agent

        correction_result = ValidationResult(
            is_valid=True, errors=[], warnings=[], corrections=["Fixed error"]
        )
        mock_validator.correct_file.return_value = correction_result

        with patch("pathlib.Path.exists", return_value=True):
            result = service.fix_agent_frontmatter("test-agent", dry_run=False)

        assert result["success"] is True
        assert result["dry_run"] is False
        assert result["corrections_made"] == ["Fixed error"]
        assert result["is_fixed"] is True

    def test_fix_all_agents(self, service, mock_validator, mock_registry):
        """Test fixing all agents."""
        mock_registry.list_agents.return_value = {
            "agent1": {"path": "/path/to/agent1.md"},
            "agent2": {"path": "/path/to/agent2.md"},
        }

        correction_results = [
            ValidationResult(is_valid=True, errors=[], warnings=[], corrections=[]),
            ValidationResult(
                is_valid=False, errors=["Error"], warnings=[], corrections=["Fix"]
            ),
        ]
        mock_validator.correct_file.side_effect = correction_results

        with patch("pathlib.Path.exists", return_value=True):
            result = service.fix_all_agents(dry_run=False)

        assert result["success"] is True
        assert result["total_agents"] == 2
        assert result["agents_checked"] == 2
        assert result["total_corrections_made"] == 1
        assert "agent2" in result["agents_fixed"]

    def test_check_agent_integrity(self, service, mock_validator, mock_registry):
        """Test checking agent file integrity."""
        mock_agent = Mock()
        mock_agent.path = "/path/to/agent.md"
        mock_registry.get_agent.return_value = mock_agent

        file_content = """---
name: Test Agent
type: executor
description: A test agent
---

Agent content here
"""

        validation_result = ValidationResult(
            is_valid=True, errors=[], warnings=[], corrections=[]
        )
        mock_validator.validate_file.return_value = validation_result
        mock_validator._extract_frontmatter.return_value = (
            "name: Test Agent\ntype: executor\ndescription: A test agent",
            "Agent content here",
        )

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=file_content):
                result = service.check_agent_integrity("test-agent")

        assert result["success"] is True
        assert result["integrity"]["file_exists"] is True
        assert result["integrity"]["has_content"] is True
        assert result["integrity"]["has_frontmatter"] is True
        assert result["integrity"]["valid_frontmatter"] is True
        assert result["is_valid"] is True
        assert result["issues"] == []

    def test_check_agent_integrity_missing_file(self, service, mock_registry):
        """Test integrity check when file is missing."""
        mock_agent = Mock()
        mock_agent.path = "/path/to/missing.md"
        mock_registry.get_agent.return_value = mock_agent

        with patch("pathlib.Path.exists", return_value=False):
            result = service.check_agent_integrity("test-agent")

        assert result["success"] is True
        assert result["integrity"]["file_exists"] is False
        assert result["is_valid"] is False
        assert "File does not exist" in result["issues"]

    def test_check_agent_integrity_no_frontmatter(self, service, mock_registry):
        """Test integrity check when frontmatter is missing."""
        mock_agent = Mock()
        mock_agent.path = "/path/to/agent.md"
        mock_registry.get_agent.return_value = mock_agent

        file_content = "Just content, no frontmatter"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=file_content):
                result = service.check_agent_integrity("test-agent")

        assert result["success"] is True
        assert result["integrity"]["has_frontmatter"] is False
        assert result["is_valid"] is False
        assert "No frontmatter found" in result["issues"]

    def test_validate_deployment_state(self, service, mock_registry):
        """Test deployment state validation."""
        mock_registry.list_agents.return_value = {
            "agent1": {"path": "/path/to/agent1.md", "name": "Agent One"},
            "agent2": {"path": "/path/to/agent2.md", "name": "Agent Two"},
            "agent3": {
                "path": "/path/to/agent3.md",
                "name": "Agent One",
            },  # Duplicate name
            "agent4": {"path": "/path/to/missing.md", "name": "Agent Four"},
        }

        # Setup file existence checks
        exists_side_effect = [True, True, True, False]
        with patch("pathlib.Path.exists", side_effect=exists_side_effect):
            result = service.validate_deployment_state()

        assert result["success"] is True
        assert result["is_healthy"] is False
        assert result["deployment_state"]["total_registered"] == 4
        assert result["deployment_state"]["files_found"] == 3
        assert len(result["deployment_state"]["files_missing"]) == 1
        assert "Agent One" in result["deployment_state"]["duplicate_names"]
        assert len(result["deployment_state"]["deployment_issues"]) > 0

    def test_validate_deployment_state_healthy(self, service, mock_registry):
        """Test deployment state validation with healthy deployment."""
        mock_registry.list_agents.return_value = {
            "agent1": {"path": "/path/to/agent1.md", "name": "Agent One"},
            "agent2": {"path": "/path/to/agent2.md", "name": "Agent Two"},
        }

        with patch("pathlib.Path.exists", return_value=True):
            result = service.validate_deployment_state()

        assert result["success"] is True
        assert result["is_healthy"] is True
        assert result["deployment_state"]["total_registered"] == 2
        assert result["deployment_state"]["files_found"] == 2
        assert len(result["deployment_state"]["files_missing"]) == 0
        assert len(result["deployment_state"]["duplicate_names"]) == 0
        assert len(result["deployment_state"]["deployment_issues"]) == 0

    def test_error_handling_in_validate_agent(self, service, mock_registry):
        """Test error handling in validate_agent."""
        mock_registry.get_agent.side_effect = Exception("Registry error")

        result = service.validate_agent("test-agent")

        assert result["success"] is False
        assert "Registry error" in result["error"]

    def test_error_handling_in_fix_all_agents(self, service, mock_registry):
        """Test error handling in fix_all_agents."""
        mock_registry.list_agents.side_effect = Exception("Registry error")

        result = service.fix_all_agents()

        assert result["success"] is False
        assert "Registry error" in result["error"]

    def test_lazy_registry_loading(self):
        """Test that registry is loaded lazily."""
        service = AgentValidationService()
        assert service._registry is None

        with patch(
            "claude_mpm.services.cli.agent_validation_service.AgentRegistryAdapter"
        ) as mock_adapter:
            mock_adapter.return_value.registry = Mock()
            _ = service.registry
            assert service._registry is not None
            mock_adapter.assert_called_once()

    def test_registry_initialization_error(self):
        """Test handling of registry initialization error."""
        service = AgentValidationService()

        with patch(
            "claude_mpm.services.cli.agent_validation_service.AgentRegistryAdapter",
            side_effect=Exception("Init error"),
        ), pytest.raises(RuntimeError, match="Could not initialize agent registry"):
            _ = service.registry
