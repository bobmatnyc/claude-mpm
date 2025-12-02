"""
Tests for Agent Dependency Service
===================================

WHY: Test the agent dependency service to ensure robust dependency management,
proper error handling, retry logic, and accurate reporting.

DESIGN DECISIONS:
- Mock external dependencies (AgentDependencyLoader, RobustPackageInstaller)
- Test all public interface methods
- Verify error handling and edge cases
- Test retry logic and network failure scenarios
"""

from unittest.mock import Mock, patch

import pytest

from claude_mpm.services.cli.agent_dependency_service import (
    AgentDependencyService,
    IAgentDependencyService,
)


class TestAgentDependencyService:
    """Test suite for AgentDependencyService."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        return AgentDependencyService()

    @pytest.fixture
    def mock_loader(self):
        """Create a mock dependency loader."""
        loader = Mock()
        loader.deployed_agents = {
            "agent1": "/path/to/agent1",
            "agent2": "/path/to/agent2",
        }
        loader.agent_dependencies = {
            "agent1": {"python": ["requests", "numpy"], "system": ["git"]},
            "agent2": {"python": ["pandas"], "system": []},
        }
        loader.auto_install = False
        return loader

    def test_interface_compliance(self, service):
        """Test that service implements the interface correctly."""
        assert isinstance(service, IAgentDependencyService)

        # Check all interface methods are implemented
        assert hasattr(service, "check_dependencies")
        assert hasattr(service, "install_dependencies")
        assert hasattr(service, "list_dependencies")
        assert hasattr(service, "fix_dependencies")
        assert hasattr(service, "validate_compatibility")
        assert hasattr(service, "get_dependency_report")

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_check_dependencies_all_agents(
        self, mock_loader_class, service, mock_loader
    ):
        """Test checking dependencies for all agents."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None
        mock_loader.analyze_dependencies.return_value = {
            "summary": {
                "missing_python": ["requests"],
                "missing_system": [],
                "installed_python": ["numpy", "pandas"],
            }
        }
        mock_loader.format_report.return_value = "Test Report"

        # Execute
        result = service.check_dependencies()

        # Verify
        assert result["success"] is True
        assert result["report"] == "Test Report"
        assert result["agent"] is None
        mock_loader.discover_deployed_agents.assert_called_once()
        mock_loader.load_agent_dependencies.assert_called_once()
        mock_loader.analyze_dependencies.assert_called_once()

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_check_dependencies_specific_agent(
        self, mock_loader_class, service, mock_loader
    ):
        """Test checking dependencies for a specific agent."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None
        mock_loader.analyze_dependencies.return_value = {
            "summary": {"missing_python": [], "missing_system": []}
        }
        mock_loader.format_report.return_value = "Agent1 Report"

        # Execute
        result = service.check_dependencies(agent_name="agent1")

        # Verify
        assert result["success"] is True
        assert result["agent"] == "agent1"
        assert mock_loader.deployed_agents == {"agent1": "/path/to/agent1"}

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_check_dependencies_unknown_agent(
        self, mock_loader_class, service, mock_loader
    ):
        """Test checking dependencies for an unknown agent."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None

        # Execute
        result = service.check_dependencies(agent_name="unknown")

        # Verify
        assert result["success"] is False
        assert "not deployed" in result["error"]
        assert result["available_agents"] == ["agent1", "agent2"]

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_install_dependencies_dry_run(
        self, mock_loader_class, service, mock_loader
    ):
        """Test dry run installation of dependencies."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None
        mock_loader.analyze_dependencies.return_value = {
            "summary": {"missing_python": ["requests", "numpy"]}
        }

        # Execute
        result = service.install_dependencies(dry_run=True)

        # Verify
        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["missing_dependencies"] == ["requests", "numpy"]
        assert "pip install" in result["install_command"]
        mock_loader.install_missing_dependencies.assert_not_called()

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_install_dependencies_success(
        self, mock_loader_class, service, mock_loader
    ):
        """Test successful installation of dependencies."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None
        mock_loader.analyze_dependencies.side_effect = [
            {"summary": {"missing_python": ["requests"]}},
            {"summary": {"missing_python": []}},  # After installation
        ]
        mock_loader.install_missing_dependencies.return_value = (True, None)
        mock_loader.checked_packages = set()

        # Execute
        result = service.install_dependencies()

        # Verify
        assert result["success"] is True
        assert result["installed"] == ["requests"]
        assert result["still_missing"] == []
        assert result["fully_resolved"] is True
        mock_loader.install_missing_dependencies.assert_called_once_with(["requests"])

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_install_dependencies_failure(
        self, mock_loader_class, service, mock_loader
    ):
        """Test failed installation of dependencies."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None
        mock_loader.analyze_dependencies.return_value = {
            "summary": {"missing_python": ["bad-package"]}
        }
        mock_loader.install_missing_dependencies.return_value = (
            False,
            "Package not found",
        )

        # Execute
        result = service.install_dependencies()

        # Verify
        assert result["success"] is False
        assert result["error"] == "Package not found"
        assert result["failed_dependencies"] == ["bad-package"]

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_list_dependencies_text_format(
        self, mock_loader_class, service, mock_loader
    ):
        """Test listing dependencies in text format."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None

        # Execute
        result = service.list_dependencies(format_type="text")

        # Verify
        assert result["success"] is True
        assert result["format"] == "text"
        assert set(result["python_dependencies"]) == {"numpy", "pandas", "requests"}
        assert result["system_dependencies"] == ["git"]
        assert "agent1" in result["per_agent"]

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_list_dependencies_json_format(
        self, mock_loader_class, service, mock_loader
    ):
        """Test listing dependencies in JSON format."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None

        # Execute
        result = service.list_dependencies(format_type="json")

        # Verify
        assert result["success"] is True
        assert result["format"] == "json"
        assert "data" in result
        assert set(result["data"]["python"]) == {"numpy", "pandas", "requests"}
        assert result["data"]["system"] == ["git"]
        assert result["data"]["agents"] == mock_loader.agent_dependencies

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_list_dependencies_pip_format(
        self, mock_loader_class, service, mock_loader
    ):
        """Test listing dependencies in pip format."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None

        # Execute
        result = service.list_dependencies(format_type="pip")

        # Verify
        assert result["success"] is True
        assert result["format"] == "pip"
        assert set(result["dependencies"]) == {"numpy", "pandas", "requests"}

    @patch("claude_mpm.services.cli.agent_dependency_service.RobustPackageInstaller")
    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_fix_dependencies_with_retry(
        self, mock_loader_class, mock_installer_class, service, mock_loader
    ):
        """Test fixing dependencies with retry logic."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_installer = Mock()
        mock_installer_class.return_value = mock_installer

        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None
        mock_loader.analyze_dependencies.side_effect = [
            {
                "summary": {
                    "missing_python": ["requests", "numpy"],
                    "missing_system": ["git"],
                }
            },
            {"summary": {"missing_python": [], "missing_system": ["git"]}},  # After fix
        ]
        mock_loader.check_python_compatibility.return_value = (
            ["requests", "numpy"],
            [],  # All compatible
        )
        mock_loader.checked_packages = set()

        mock_installer.install_packages.return_value = (
            ["requests", "numpy"],  # successful
            [],  # failed
            {},  # errors
        )

        # Execute
        result = service.fix_dependencies(max_retries=5)

        # Verify
        assert result["success"] is True
        assert result["fixed_python"] == ["requests", "numpy"]
        assert result["failed_python"] == []
        assert result["missing_system"] == ["git"]
        assert result["still_missing"] == []
        mock_installer_class.assert_called_once_with(
            max_retries=5, retry_delay=2.0, timeout=300
        )
        mock_installer.install_packages.assert_called_once()

    @patch("claude_mpm.services.cli.agent_dependency_service.RobustPackageInstaller")
    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_fix_dependencies_with_incompatible(
        self, mock_loader_class, mock_installer_class, service, mock_loader
    ):
        """Test fixing dependencies with incompatible packages."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_installer = Mock()
        mock_installer_class.return_value = mock_installer

        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None
        mock_loader.analyze_dependencies.return_value = {
            "summary": {
                "missing_python": ["requests", "old-package"],
                "missing_system": [],
            }
        }
        mock_loader.check_python_compatibility.return_value = (
            ["requests"],  # compatible
            ["old-package"],  # incompatible
        )
        mock_loader.checked_packages = set()

        mock_installer.install_packages.return_value = (["requests"], [], {})

        # Execute
        result = service.fix_dependencies()

        # Verify
        assert result["success"] is True
        assert result["incompatible"] == ["old-package"]
        assert result["fixed_python"] == ["requests"]
        mock_installer.install_packages.assert_called_once_with(["requests"])

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_fix_dependencies_no_agents(self, mock_loader_class, service):
        """Test fixing dependencies when no agents are deployed."""
        # Setup
        mock_loader = Mock()
        mock_loader.deployed_agents = {}
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None

        # Execute
        result = service.fix_dependencies()

        # Verify
        assert result["success"] is True
        assert result["message"] == "No deployed agents found"

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_validate_compatibility(self, mock_loader_class, service, mock_loader):
        """Test package compatibility validation."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.check_python_compatibility.return_value = (
            ["requests", "numpy"],
            ["old-lib"],
        )

        # Execute
        compatible, incompatible = service.validate_compatibility(
            ["requests", "numpy", "old-lib"]
        )

        # Verify
        assert compatible == ["requests", "numpy"]
        assert incompatible == ["old-lib"]
        mock_loader.check_python_compatibility.assert_called_once_with(
            ["requests", "numpy", "old-lib"]
        )

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_get_dependency_report(self, mock_loader_class, service, mock_loader):
        """Test generating a dependency report."""
        # Setup
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.return_value = None
        mock_loader.load_agent_dependencies.return_value = None
        mock_loader.analyze_dependencies.return_value = {
            "summary": {"missing_python": [], "missing_system": []}
        }
        mock_loader.format_report.return_value = "Dependency Report Content"

        # Execute
        report = service.get_dependency_report()

        # Verify
        assert report == "Dependency Report Content"
        mock_loader.discover_deployed_agents.assert_called_once()
        mock_loader.load_agent_dependencies.assert_called_once()
        mock_loader.analyze_dependencies.assert_called_once()
        mock_loader.format_report.assert_called_once()

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_error_handling_check_dependencies(self, mock_loader_class, service):
        """Test error handling in check_dependencies."""
        # Setup
        mock_loader_class.side_effect = Exception("Connection error")

        # Execute
        result = service.check_dependencies()

        # Verify
        assert result["success"] is False
        assert "Connection error" in result["error"]

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_error_handling_install_dependencies(self, mock_loader_class, service):
        """Test error handling in install_dependencies."""
        # Setup
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        mock_loader.discover_deployed_agents.side_effect = Exception("Network timeout")

        # Execute
        result = service.install_dependencies()

        # Verify
        assert result["success"] is False
        assert "Network timeout" in result["error"]

    @patch("claude_mpm.services.cli.agent_dependency_service.AgentDependencyLoader")
    def test_loader_caching(self, mock_loader_class, service):
        """Test that loader is cached and reused when auto_install matches."""
        # Setup
        mock_loader1 = Mock(auto_install=False)
        mock_loader2 = Mock(auto_install=True)
        mock_loader_class.side_effect = [mock_loader1, mock_loader2]

        # Execute - first call creates loader with auto_install=False
        service._get_loader(auto_install=False)
        loader1 = service.loader

        # Second call with same auto_install should reuse
        service._get_loader(auto_install=False)
        loader2 = service.loader

        # Third call with different auto_install should create new
        service._get_loader(auto_install=True)
        loader3 = service.loader

        # Verify
        assert loader1 is loader2  # Same instance
        assert loader1 is not loader3  # Different instance
        assert mock_loader_class.call_count == 2  # Only called twice
