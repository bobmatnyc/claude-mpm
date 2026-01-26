"""
Tests for the OAuth command, specifically the MCP configuration functionality.

WHY: The OAuth setup command now ensures MCP server is configured in .mcp.json
after successful OAuth authentication. This is critical for users to have a
seamless setup experience.

DESIGN DECISIONS:
- Test _ensure_mcp_configured function in isolation
- Test _detect_google_credentials function for credential detection
- Test various scenarios: new file, existing file, already configured
- Mock file operations to avoid side effects
- Verify JSON structure is correct
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.cli.commands.oauth import (
    _detect_google_credentials,
    _ensure_mcp_configured,
)


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


class TestDetectGoogleCredentials:
    """Test _detect_google_credentials function."""

    def test_detects_from_environment_variables(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Test detecting credentials from environment variables (highest priority)."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "env-client-id")
        monkeypatch.setenv(
            "GOOGLE_OAUTH_CLIENT_SECRET", "env-client-secret"
        )  # pragma: allowlist secret

        # Also create .env file to verify environment takes priority
        env_path = tmp_path / ".env"
        env_path.write_text(
            'GOOGLE_OAUTH_CLIENT_ID="file-client-id"\n'
            'GOOGLE_OAUTH_CLIENT_SECRET="file-client-secret"\n'  # pragma: allowlist secret
        )

        client_id, client_secret, source = _detect_google_credentials()

        assert client_id == "env-client-id"
        assert client_secret == "env-client-secret"  # pragma: allowlist secret
        assert source == "environment"

    def test_detects_from_env_local_file(self, tmp_path: Path, monkeypatch) -> None:
        """Test detecting credentials from .env.local file (second priority)."""
        monkeypatch.chdir(tmp_path)
        # Clear environment variables
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)

        # Create both .env.local and .env to verify priority
        env_local_path = tmp_path / ".env.local"
        env_local_path.write_text(
            'GOOGLE_OAUTH_CLIENT_ID="local-client-id"\n'
            'GOOGLE_OAUTH_CLIENT_SECRET="local-client-secret"\n'  # pragma: allowlist secret
        )

        env_path = tmp_path / ".env"
        env_path.write_text(
            'GOOGLE_OAUTH_CLIENT_ID="default-client-id"\n'
            'GOOGLE_OAUTH_CLIENT_SECRET="default-client-secret"\n'  # pragma: allowlist secret
        )

        client_id, client_secret, source = _detect_google_credentials()

        assert client_id == "local-client-id"
        assert client_secret == "local-client-secret"  # pragma: allowlist secret
        assert source == ".env.local"

    def test_detects_from_env_file(self, tmp_path: Path, monkeypatch) -> None:
        """Test detecting credentials from .env file (lowest priority)."""
        monkeypatch.chdir(tmp_path)
        # Clear environment variables
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)

        # Only create .env file
        env_path = tmp_path / ".env"
        env_path.write_text(
            'GOOGLE_OAUTH_CLIENT_ID="default-client-id"\n'
            'GOOGLE_OAUTH_CLIENT_SECRET="default-client-secret"\n'  # pragma: allowlist secret
        )

        client_id, client_secret, source = _detect_google_credentials()

        assert client_id == "default-client-id"
        assert client_secret == "default-client-secret"  # pragma: allowlist secret
        assert source == ".env"

    def test_returns_none_when_not_found(self, tmp_path: Path, monkeypatch) -> None:
        """Test returning None when no credentials found."""
        monkeypatch.chdir(tmp_path)
        # Clear environment variables
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)

        client_id, client_secret, source = _detect_google_credentials()

        assert client_id is None
        assert client_secret is None
        assert source is None

    def test_returns_none_when_only_client_id_in_env(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Test returning None when only client ID is found (incomplete credentials)."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "only-client-id")
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)

        client_id, client_secret, source = _detect_google_credentials()

        assert client_id is None
        assert client_secret is None
        assert source is None

    def test_handles_quoted_values_in_env_file(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Test handling of quoted values in .env files."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)

        # Create .env with various quote styles
        env_path = tmp_path / ".env"
        env_path.write_text(
            'GOOGLE_OAUTH_CLIENT_ID="double-quoted"\n'
            "GOOGLE_OAUTH_CLIENT_SECRET='single-quoted'\n"  # pragma: allowlist secret
        )

        client_id, client_secret, source = _detect_google_credentials()

        assert client_id == "double-quoted"
        assert client_secret == "single-quoted"  # pragma: allowlist secret
        assert source == ".env"

    def test_skips_comments_in_env_file(self, tmp_path: Path, monkeypatch) -> None:
        """Test that comments in .env files are skipped."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)

        env_path = tmp_path / ".env"
        env_path.write_text(
            "# This is a comment\n"
            'GOOGLE_OAUTH_CLIENT_ID="valid-id"\n'
            "# Another comment\n"
            'GOOGLE_OAUTH_CLIENT_SECRET="valid-secret"\n'  # pragma: allowlist secret
        )

        client_id, client_secret, source = _detect_google_credentials()

        assert client_id == "valid-id"
        assert client_secret == "valid-secret"  # pragma: allowlist secret
        assert source == ".env"
