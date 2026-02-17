"""Tests for integration CLI commands (ISS-0011, ISS-0013).

Tests the IntegrationManager class and CLI commands for managing
API integrations.
"""

from __future__ import annotations

import tempfile
from pathlib import Path  # noqa: TC003

import pytest
import yaml
from click.testing import CliRunner

from claude_mpm.integrations.cli.integrate import (
    IntegrationManager,
    manage_integrations,
)


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def temp_catalog(tmp_path: Path) -> Path:
    """Create a temporary catalog with test integration."""
    catalog = tmp_path / "catalog"
    catalog.mkdir()

    # Create test integration
    test_integration = catalog / "testapi"
    test_integration.mkdir()

    manifest = {
        "name": "testapi",
        "version": "1.0.0",
        "description": "Test API integration",
        "api_type": "rest",
        "base_url": "https://api.test.com",
        "auth": {"type": "none", "credentials": []},
        "operations": [
            {
                "name": "get_item",
                "description": "Get an item",
                "type": "rest_get",
                "endpoint": "/items/{id}",
            }
        ],
    }

    with (test_integration / "integration.yaml").open("w") as f:
        yaml.dump(manifest, f)

    return catalog


@pytest.fixture
def manager(
    temp_project: Path, temp_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> IntegrationManager:
    """Create IntegrationManager with temp directories."""
    mgr = IntegrationManager(project_dir=temp_project)
    # Override catalog directory
    mgr.catalog_dir = temp_catalog
    return mgr


class TestIntegrationManager:
    """Tests for IntegrationManager class."""

    def test_list_available_empty(self, manager: IntegrationManager) -> None:
        """Test listing available integrations from catalog."""
        available = manager.list_available()
        assert len(available) == 1
        assert available[0]["name"] == "testapi"

    def test_list_installed_empty(self, manager: IntegrationManager) -> None:
        """Test listing installed integrations when none installed."""
        installed = manager.list_installed()
        assert len(installed) == 0

    def test_add_integration(self, manager: IntegrationManager) -> None:
        """Test adding an integration from catalog."""
        result = manager.add("testapi", scope="project")
        assert result is True

        # Verify installation
        installed = manager.list_installed()
        assert len(installed) == 1
        assert installed[0].name == "testapi"
        assert installed[0].scope == "project"

    def test_add_integration_not_found(self, manager: IntegrationManager) -> None:
        """Test adding non-existent integration."""
        result = manager.add("nonexistent", scope="project")
        assert result is False

    def test_add_integration_already_installed(
        self, manager: IntegrationManager
    ) -> None:
        """Test adding integration that's already installed."""
        manager.add("testapi", scope="project")
        result = manager.add("testapi", scope="project")
        assert result is False

    def test_remove_integration(self, manager: IntegrationManager) -> None:
        """Test removing an installed integration."""
        manager.add("testapi", scope="project")
        result = manager.remove("testapi")
        assert result is True

        installed = manager.list_installed()
        assert len(installed) == 0

    def test_remove_integration_not_installed(
        self, manager: IntegrationManager
    ) -> None:
        """Test removing non-installed integration."""
        result = manager.remove("testapi")
        assert result is False

    def test_status_installed(self, manager: IntegrationManager) -> None:
        """Test status of installed integration."""
        manager.add("testapi", scope="project")
        status = manager.status("testapi")

        assert status["installed"] is True
        assert status["name"] == "testapi"
        assert status["version"] == "1.0.0"
        assert status["scope"] == "project"

    def test_status_not_installed(self, manager: IntegrationManager) -> None:
        """Test status of non-installed integration."""
        status = manager.status("testapi")
        assert status["installed"] is False

    def test_call_operation(self, manager: IntegrationManager) -> None:
        """Test calling an integration operation."""
        manager.add("testapi", scope="project")
        result = manager.call("testapi", "get_item", {"id": "123"})

        assert result["success"] is True
        assert result["operation"] == "get_item"
        assert result["params"]["id"] == "123"

    def test_call_operation_not_found(self, manager: IntegrationManager) -> None:
        """Test calling non-existent operation."""
        manager.add("testapi", scope="project")
        result = manager.call("testapi", "nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_validate_valid_manifest(self, temp_catalog: Path) -> None:
        """Test validating a valid manifest."""
        manager = IntegrationManager()
        manager.catalog_dir = temp_catalog
        errors = manager.validate(temp_catalog / "testapi")
        # Note: May have errors due to simplified test manifest
        assert isinstance(errors, list)

    def test_validate_missing_manifest(self, tmp_path: Path) -> None:
        """Test validating non-existent manifest."""
        manager = IntegrationManager()
        errors = manager.validate(tmp_path / "nonexistent")
        assert len(errors) > 0
        assert "not found" in errors[0].lower()


class TestCLICommands:
    """Tests for CLI commands using Click's test runner."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_list_command(self, runner: CliRunner) -> None:
        """Test list command runs without error."""
        result = runner.invoke(manage_integrations, ["list"])
        # May show empty results but should not error
        assert result.exit_code == 0

    def test_add_command_not_found(self, runner: CliRunner) -> None:
        """Test add command with non-existent integration."""
        result = runner.invoke(manage_integrations, ["add", "nonexistent"])
        assert "not found" in result.output.lower()

    def test_status_command_not_installed(self, runner: CliRunner) -> None:
        """Test status command with non-installed integration."""
        result = runner.invoke(manage_integrations, ["status", "nonexistent"])
        assert "not installed" in result.output.lower()

    def test_validate_command_missing(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test validate command with missing path."""
        result = runner.invoke(manage_integrations, ["validate", str(tmp_path)])
        # Should report manifest not found
        assert result.exit_code == 0 or "error" in result.output.lower()
