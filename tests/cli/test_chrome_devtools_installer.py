"""
Tests for Chrome DevTools MCP Auto-Installer
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.cli.chrome_devtools_installer import (
    ChromeDevToolsInstaller,
    auto_install_chrome_devtools,
)


@pytest.fixture
def installer():
    """Create a ChromeDevToolsInstaller instance for testing."""
    return ChromeDevToolsInstaller()


@pytest.fixture
def mock_claude_config(tmp_path):
    """Create a mock Claude config file."""
    config_file = tmp_path / ".claude.json"
    return config_file


class TestChromeDevToolsInstaller:
    """Test suite for ChromeDevToolsInstaller."""

    def test_is_already_configured_when_configured(self, installer, mock_claude_config):
        """Test that is_already_configured returns True when chrome-devtools is configured."""
        # Setup: Create config with chrome-devtools
        config = {
            "mcpServers": {
                "chrome-devtools": {
                    "command": "npx",
                    "args": ["chrome-devtools-mcp@latest"],
                }
            }
        }
        mock_claude_config.write_text(json.dumps(config))

        # Mock the config path
        with patch.object(installer, "claude_config_path", mock_claude_config):
            assert installer.is_already_configured() is True

    def test_is_already_configured_when_not_configured(
        self, installer, mock_claude_config
    ):
        """Test that is_already_configured returns False when chrome-devtools is not configured."""
        # Setup: Create config without chrome-devtools
        config = {"mcpServers": {}}
        mock_claude_config.write_text(json.dumps(config))

        # Mock the config path
        with patch.object(installer, "claude_config_path", mock_claude_config):
            assert installer.is_already_configured() is False

    def test_is_already_configured_when_config_missing(self, installer, tmp_path):
        """Test that is_already_configured returns False when config file doesn't exist."""
        non_existent_config = tmp_path / "non_existent.json"

        with patch.object(installer, "claude_config_path", non_existent_config):
            assert installer.is_already_configured() is False

    def test_is_already_configured_with_invalid_json(
        self, installer, mock_claude_config
    ):
        """Test that is_already_configured handles invalid JSON gracefully."""
        # Setup: Create invalid JSON
        mock_claude_config.write_text("{invalid json}")

        with patch.object(installer, "claude_config_path", mock_claude_config):
            assert installer.is_already_configured() is False

    @patch("subprocess.run")
    def test_install_mcp_server_success(self, mock_run, installer):
        """Test successful MCP server installation."""
        # Setup: Mock successful subprocess run
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        # Execute
        success, error = installer.install_mcp_server()

        # Assert
        assert success is True
        assert error is None
        mock_run.assert_called_once()

        # Verify command arguments
        args = mock_run.call_args[0][0]
        assert args[0] == "claude"
        assert args[1] == "mcp"
        assert args[2] == "add"
        assert args[3] == "chrome-devtools"
        assert args[4] == "--"
        assert "npx" in args
        assert "chrome-devtools-mcp@latest" in args

    @patch("subprocess.run")
    def test_install_mcp_server_failure(self, mock_run, installer):
        """Test MCP server installation failure."""
        # Setup: Mock failed subprocess run
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="Installation failed"
        )

        # Execute
        success, error = installer.install_mcp_server()

        # Assert
        assert success is False
        assert error is not None
        assert "Installation failed" in error

    @patch("subprocess.run")
    def test_install_mcp_server_timeout(self, mock_run, installer):
        """Test MCP server installation timeout."""
        # Setup: Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

        # Execute
        success, error = installer.install_mcp_server()

        # Assert
        assert success is False
        assert error is not None
        assert "timed out" in error.lower()

    @patch("subprocess.run")
    def test_install_mcp_server_claude_not_found(self, mock_run, installer):
        """Test MCP server installation when Claude CLI is not found."""
        # Setup: Mock FileNotFoundError
        mock_run.side_effect = FileNotFoundError("claude not found")

        # Execute
        success, error = installer.install_mcp_server()

        # Assert
        assert success is False
        assert error is not None
        assert "Claude CLI not found" in error

    def test_auto_install_when_already_configured(self, installer, mock_claude_config):
        """Test auto_install when chrome-devtools is already configured."""
        # Setup: Configure chrome-devtools
        config = {
            "mcpServers": {
                "chrome-devtools": {
                    "command": "npx",
                    "args": ["chrome-devtools-mcp@latest"],
                }
            }
        }
        mock_claude_config.write_text(json.dumps(config))

        with patch.object(installer, "claude_config_path", mock_claude_config):
            # Should return True without attempting installation
            with patch.object(
                installer, "install_mcp_server"
            ) as mock_install:
                result = installer.auto_install(quiet=True)

                assert result is True
                mock_install.assert_not_called()

    def test_auto_install_when_not_configured(self, installer, mock_claude_config):
        """Test auto_install when chrome-devtools is not configured."""
        # Setup: Empty config
        config = {"mcpServers": {}}
        mock_claude_config.write_text(json.dumps(config))

        with patch.object(installer, "claude_config_path", mock_claude_config):
            # Mock successful installation
            with patch.object(
                installer, "install_mcp_server", return_value=(True, None)
            ):
                result = installer.auto_install(quiet=True)

                assert result is True

    def test_auto_install_when_installation_fails(self, installer, mock_claude_config):
        """Test auto_install when installation fails."""
        # Setup: Empty config
        config = {"mcpServers": {}}
        mock_claude_config.write_text(json.dumps(config))

        with patch.object(installer, "claude_config_path", mock_claude_config):
            # Mock failed installation
            with patch.object(
                installer,
                "install_mcp_server",
                return_value=(False, "Installation failed"),
            ):
                result = installer.auto_install(quiet=True)

                assert result is False


class TestConvenienceFunction:
    """Test the convenience function."""

    @patch("claude_mpm.cli.chrome_devtools_installer.ChromeDevToolsInstaller")
    def test_auto_install_chrome_devtools(self, mock_installer_class):
        """Test the convenience function delegates to ChromeDevToolsInstaller."""
        # Setup
        mock_installer = MagicMock()
        mock_installer.auto_install.return_value = True
        mock_installer_class.return_value = mock_installer

        # Execute
        result = auto_install_chrome_devtools(quiet=True)

        # Assert
        assert result is True
        mock_installer_class.assert_called_once()
        mock_installer.auto_install.assert_called_once_with(quiet=True)
