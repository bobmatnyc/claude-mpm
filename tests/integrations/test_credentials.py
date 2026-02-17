"""Tests for credential management."""

import os

import pytest

from claude_mpm.integrations.core.credentials import CredentialManager
from claude_mpm.integrations.core.manifest import CredentialDefinition


class TestCredentialManager:
    """Tests for CredentialManager class."""

    @pytest.fixture
    def cred_manager(self, tmp_path) -> CredentialManager:
        """Create credential manager with temp project dir."""
        return CredentialManager(project_dir=tmp_path)

    @pytest.fixture
    def sample_credentials(self) -> list[CredentialDefinition]:
        """Sample credential definitions."""
        return [
            CredentialDefinition(
                name="API_KEY",
                prompt="Enter API key",
                help="Get from settings",
                required=True,
            ),
            CredentialDefinition(
                name="SECRET",
                prompt="Enter secret",
                required=False,
            ),
        ]

    def test_get_from_env(self, cred_manager: CredentialManager, monkeypatch) -> None:
        """Test getting credential from environment."""
        monkeypatch.setenv("TEST_API_KEY", "env_value")

        value = cred_manager.get("TEST_API_KEY")
        assert value == "env_value"

    def test_get_from_project_env_local(self, cred_manager: CredentialManager) -> None:
        """Test getting credential from .env.local."""
        # Create .env.local file
        env_local = cred_manager.project_env_local
        env_local.write_text('LOCAL_KEY="local_value"\n')

        value = cred_manager.get("LOCAL_KEY")
        assert value == "local_value"

    def test_get_from_project_env(self, cred_manager: CredentialManager) -> None:
        """Test getting credential from .env."""
        # Create .env file
        env_file = cred_manager.project_env
        env_file.write_text("PROJECT_KEY=project_value\n")  # pragma: allowlist secret

        value = cred_manager.get("PROJECT_KEY")
        assert value == "project_value"

    def test_get_priority_env_over_file(
        self, cred_manager: CredentialManager, monkeypatch
    ) -> None:
        """Test env vars take priority over files."""
        monkeypatch.setenv("PRIORITY_KEY", "env_value")

        # Create .env file with different value
        env_file = cred_manager.project_env
        env_file.write_text('PRIORITY_KEY="file_value"\n')

        value = cred_manager.get("PRIORITY_KEY")
        assert value == "env_value"

    def test_get_priority_env_local_over_env(
        self, cred_manager: CredentialManager
    ) -> None:
        """Test .env.local takes priority over .env."""
        # Create .env with one value
        cred_manager.project_env.write_text('KEY="env_value"\n')

        # Create .env.local with different value
        cred_manager.project_env_local.write_text('KEY="local_value"\n')

        value = cred_manager.get("KEY")
        assert value == "local_value"

    def test_get_not_found(self, cred_manager: CredentialManager) -> None:
        """Test getting nonexistent credential."""
        value = cred_manager.get("NONEXISTENT_KEY")
        assert value is None

    def test_set_project_scope(self, cred_manager: CredentialManager) -> None:
        """Test setting credential with project scope."""
        cred_manager.set("NEW_KEY", "new_value", scope="project")

        # Should be in .env.local
        content = cred_manager.project_env_local.read_text()
        assert 'NEW_KEY="new_value"' in content

    def test_set_user_scope(self, cred_manager: CredentialManager, tmp_path) -> None:
        """Test setting credential with user scope."""
        # Override user env path for testing
        cred_manager.user_env = tmp_path / "user" / ".env"

        cred_manager.set("USER_KEY", "user_value", scope="user")

        content = cred_manager.user_env.read_text()
        assert 'USER_KEY="user_value"' in content

    def test_set_updates_existing(self, cred_manager: CredentialManager) -> None:
        """Test setting credential updates existing value."""
        cred_manager.set("KEY", "value1", scope="project")
        cred_manager.set("KEY", "value2", scope="project")

        content = cred_manager.project_env_local.read_text()
        assert 'KEY="value2"' in content
        assert content.count("KEY=") == 1

    def test_mask_short_value(self, cred_manager: CredentialManager) -> None:
        """Test masking short credential value."""
        masked = cred_manager.mask("short")
        assert masked == "*****"

    def test_mask_long_value(self, cred_manager: CredentialManager) -> None:
        """Test masking long credential value."""
        masked = cred_manager.mask("this_is_a_long_api_key")
        assert masked == "this**************_key"
        assert len(masked) == len("this_is_a_long_api_key")

    def test_mask_empty(self, cred_manager: CredentialManager) -> None:
        """Test masking empty value."""
        masked = cred_manager.mask("")
        assert masked == ""

    def test_has_credential_true(
        self, cred_manager: CredentialManager, monkeypatch
    ) -> None:
        """Test has_credential returns True when exists."""
        monkeypatch.setenv("EXISTS_KEY", "value")
        assert cred_manager.has_credential("EXISTS_KEY") is True

    def test_has_credential_false(self, cred_manager: CredentialManager) -> None:
        """Test has_credential returns False when missing."""
        assert cred_manager.has_credential("MISSING_KEY") is False

    def test_get_all_credentials(
        self,
        cred_manager: CredentialManager,
        sample_credentials: list[CredentialDefinition],
        monkeypatch,
    ) -> None:
        """Test getting all credentials."""
        monkeypatch.setenv("API_KEY", "key_value")

        found, missing = cred_manager.get_all_credentials(sample_credentials)

        assert "API_KEY" in found
        assert found["API_KEY"] == "key_value"  # pragma: allowlist secret
        assert "SECRET" not in missing  # Optional, so not in missing

    def test_get_all_credentials_missing_required(
        self,
        cred_manager: CredentialManager,
        sample_credentials: list[CredentialDefinition],
    ) -> None:
        """Test missing required credentials reported."""
        _found, missing = cred_manager.get_all_credentials(sample_credentials)

        assert "API_KEY" in missing
        assert "SECRET" not in missing  # Optional

    def test_delete_project_scope(self, cred_manager: CredentialManager) -> None:
        """Test deleting credential from project scope."""
        # Set credential
        cred_manager.set("DELETE_KEY", "value", scope="project")
        assert cred_manager.get("DELETE_KEY") == "value"

        # Delete it
        result = cred_manager.delete("DELETE_KEY", scope="project")
        assert result is True
        assert cred_manager.get("DELETE_KEY") is None

    def test_delete_not_found(self, cred_manager: CredentialManager) -> None:
        """Test deleting nonexistent credential."""
        result = cred_manager.delete("NONEXISTENT", scope="project")
        assert result is False


class TestEnvFileParsing:
    """Tests for .env file parsing edge cases."""

    @pytest.fixture
    def cred_manager(self, tmp_path) -> CredentialManager:
        """Create credential manager with temp project dir."""
        return CredentialManager(project_dir=tmp_path)

    def test_parse_unquoted_value(self, cred_manager: CredentialManager) -> None:
        """Test parsing unquoted values."""
        cred_manager.project_env.write_text("KEY=unquoted_value\n")

        value = cred_manager.get("KEY")
        assert value == "unquoted_value"

    def test_parse_double_quoted_value(self, cred_manager: CredentialManager) -> None:
        """Test parsing double-quoted values."""
        cred_manager.project_env.write_text('KEY="quoted value"\n')

        value = cred_manager.get("KEY")
        assert value == "quoted value"

    def test_parse_single_quoted_value(self, cred_manager: CredentialManager) -> None:
        """Test parsing single-quoted values."""
        cred_manager.project_env.write_text("KEY='single quoted'\n")

        value = cred_manager.get("KEY")
        assert value == "single quoted"

    def test_skip_comments(self, cred_manager: CredentialManager) -> None:
        """Test comments are skipped."""
        content = """# This is a comment
KEY=value
# Another comment
OTHER=other_value
"""
        cred_manager.project_env.write_text(content)

        assert cred_manager.get("KEY") == "value"
        assert cred_manager.get("OTHER") == "other_value"

    def test_skip_empty_lines(self, cred_manager: CredentialManager) -> None:
        """Test empty lines are skipped."""
        content = """KEY=value

OTHER=other_value

"""
        cred_manager.project_env.write_text(content)

        assert cred_manager.get("KEY") == "value"
        assert cred_manager.get("OTHER") == "other_value"

    def test_handle_whitespace(self, cred_manager: CredentialManager) -> None:
        """Test whitespace handling."""
        cred_manager.project_env.write_text("  KEY=value  \n")

        value = cred_manager.get("KEY")
        assert value == "value"
