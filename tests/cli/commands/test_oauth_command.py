"""
Tests for the OAuth command, specifically the MCP configuration functionality.

WHY: The OAuth setup command now ensures MCP server is configured in .mcp.json
after successful OAuth authentication. This is critical for users to have a
seamless setup experience.

DESIGN DECISIONS:
- Test _ensure_mcp_configured function in isolation
- Test various scenarios: new file, existing file, already configured
- Mock file operations to avoid side effects
- Verify JSON structure is correct
"""

import json
import tempfile
from pathlib import Path

import pytest

from claude_mpm.cli.commands.oauth import _ensure_mcp_configured


class TestEnsureMcpConfigured:
    """Test _ensure_mcp_configured function."""

    def test_skips_non_workspace_mcp_service(self, tmp_path: Path) -> None:
        """Test that non-workspace-mcp services are skipped."""
        result = _ensure_mcp_configured("other-service", tmp_path)
        assert result is False
        assert not (tmp_path / ".mcp.json").exists()

    def test_creates_new_mcp_json(self, tmp_path: Path) -> None:
        """Test creating new .mcp.json when it doesn't exist."""
        result = _ensure_mcp_configured("workspace-mcp", tmp_path)

        assert result is True
        mcp_config_path = tmp_path / ".mcp.json"
        assert mcp_config_path.exists()

        with open(mcp_config_path) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "google-workspace-mcp" in config["mcpServers"]
        assert (
            config["mcpServers"]["google-workspace-mcp"]["command"]
            == "google-workspace-mcp"
        )
        assert config["mcpServers"]["google-workspace-mcp"]["args"] == []

    def test_adds_to_existing_mcp_json(self, tmp_path: Path) -> None:
        """Test adding to existing .mcp.json with other servers."""
        mcp_config_path = tmp_path / ".mcp.json"

        # Create existing config with another server
        existing_config = {
            "mcpServers": {
                "other-server": {"command": "other-command", "args": ["--flag"]}
            }
        }
        with open(mcp_config_path, "w") as f:
            json.dump(existing_config, f)

        result = _ensure_mcp_configured("workspace-mcp", tmp_path)

        assert result is True
        with open(mcp_config_path) as f:
            config = json.load(f)

        # Should preserve existing server
        assert "other-server" in config["mcpServers"]
        assert config["mcpServers"]["other-server"]["command"] == "other-command"

        # Should add new server
        assert "google-workspace-mcp" in config["mcpServers"]
        assert (
            config["mcpServers"]["google-workspace-mcp"]["command"]
            == "google-workspace-mcp"
        )

    def test_skips_if_already_configured(self, tmp_path: Path) -> None:
        """Test that already configured server is not modified."""
        mcp_config_path = tmp_path / ".mcp.json"

        # Create existing config with google-workspace-mcp already configured
        existing_config = {
            "mcpServers": {
                "google-workspace-mcp": {"command": "google-workspace-mcp", "args": []}
            }
        }
        with open(mcp_config_path, "w") as f:
            json.dump(existing_config, f)

        result = _ensure_mcp_configured("workspace-mcp", tmp_path)

        # Should return False because already configured
        assert result is False

    def test_fixes_incorrect_config(self, tmp_path: Path) -> None:
        """Test that incorrect configuration is fixed."""
        mcp_config_path = tmp_path / ".mcp.json"

        # Create existing config with wrong command
        existing_config = {
            "mcpServers": {
                "google-workspace-mcp": {"command": "wrong-command", "args": []}
            }
        }
        with open(mcp_config_path, "w") as f:
            json.dump(existing_config, f)

        result = _ensure_mcp_configured("workspace-mcp", tmp_path)

        # Should return True because it fixed the config
        assert result is True

        with open(mcp_config_path) as f:
            config = json.load(f)

        assert (
            config["mcpServers"]["google-workspace-mcp"]["command"]
            == "google-workspace-mcp"
        )

    def test_handles_empty_mcp_json(self, tmp_path: Path) -> None:
        """Test handling of empty .mcp.json file."""
        mcp_config_path = tmp_path / ".mcp.json"

        # Create empty config
        with open(mcp_config_path, "w") as f:
            json.dump({}, f)

        result = _ensure_mcp_configured("workspace-mcp", tmp_path)

        assert result is True
        with open(mcp_config_path) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "google-workspace-mcp" in config["mcpServers"]

    def test_handles_malformed_json(self, tmp_path: Path) -> None:
        """Test handling of malformed JSON file."""
        mcp_config_path = tmp_path / ".mcp.json"

        # Create malformed JSON
        with open(mcp_config_path, "w") as f:
            f.write("{ invalid json }")

        result = _ensure_mcp_configured("workspace-mcp", tmp_path)

        # Should still succeed by creating new config
        assert result is True
        with open(mcp_config_path) as f:
            config = json.load(f)

        assert "google-workspace-mcp" in config["mcpServers"]
