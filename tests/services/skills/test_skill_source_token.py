"""Tests for skill source token authentication.

Tests per-source token support for private GitHub repositories.
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.config.skill_sources import SkillSource, SkillSourceConfiguration
from claude_mpm.services.skills.git_skill_source_manager import _get_github_token


class TestSkillSourceTokenField:
    """Test SkillSource token field persistence."""

    def test_skill_source_with_token(self):
        """Token field should be optional and stored in SkillSource."""
        source = SkillSource(
            id="private-repo",
            type="git",
            url="https://github.com/owner/private-repo",
            token="$PRIVATE_TOKEN",
        )

        assert source.token == "$PRIVATE_TOKEN"
        assert source.branch == "main"
        assert source.priority == 100

    def test_skill_source_without_token(self):
        """SkillSource should work without token (backward compatible)."""
        source = SkillSource(
            id="public-repo",
            type="git",
            url="https://github.com/owner/public-repo",
        )

        assert source.token is None

    def test_skill_source_direct_token(self):
        """SkillSource should accept direct token values."""
        source = SkillSource(
            id="direct-token",
            type="git",
            url="https://github.com/owner/repo",
            token="ghp_directtoken123",
        )

        assert source.token == "ghp_directtoken123"


class TestSkillSourceConfigurationTokenPersistence:
    """Test token field persistence to/from YAML."""

    def test_save_and_load_with_token(self, tmp_path):
        """Token should persist to YAML and load correctly."""
        config_path = tmp_path / "skill_sources.yaml"
        config = SkillSourceConfiguration(config_path=config_path)

        # Create source with token
        source = SkillSource(
            id="private",
            type="git",
            url="https://github.com/owner/private",
            token="$PRIVATE_TOKEN",
        )

        # Save
        config.save([source])

        # Load
        loaded_sources = config.load()

        assert len(loaded_sources) == 1
        assert loaded_sources[0].token == "$PRIVATE_TOKEN"

    def test_save_without_token_backward_compatible(self, tmp_path):
        """Sources without token should not include token field in YAML."""
        config_path = tmp_path / "skill_sources.yaml"
        config = SkillSourceConfiguration(config_path=config_path)

        # Create source without token
        source = SkillSource(
            id="public",
            type="git",
            url="https://github.com/owner/public",
        )

        # Save
        config.save([source])

        # Verify YAML doesn't include token field
        yaml_content = config_path.read_text()
        assert "token:" not in yaml_content

        # Load should work without token field
        loaded_sources = config.load()
        assert len(loaded_sources) == 1
        assert loaded_sources[0].token is None

    def test_load_legacy_yaml_without_token(self, tmp_path):
        """Loading YAML without token field should default to None."""
        config_path = tmp_path / "skill_sources.yaml"
        config_path.write_text(
            """sources:
  - id: legacy
    type: git
    url: https://github.com/owner/legacy
    branch: main
    priority: 100
    enabled: true
"""
        )

        config = SkillSourceConfiguration(config_path=config_path)
        sources = config.load()

        assert len(sources) == 1
        assert sources[0].token is None


class TestTokenResolution:
    """Test _get_github_token() token resolution logic."""

    def test_env_var_resolution(self):
        """Token starting with $ should resolve from environment."""
        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo",
            token="$MY_CUSTOM_TOKEN",
        )

        with patch.dict(os.environ, {"MY_CUSTOM_TOKEN": "resolved_token_value"}):
            token = _get_github_token(source)
            assert token == "resolved_token_value"

    def test_env_var_missing(self):
        """Missing env var should return None."""
        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo",
            token="$NONEXISTENT_TOKEN",
        )

        with patch.dict(os.environ, {}, clear=True):
            token = _get_github_token(source)
            assert token is None

    def test_direct_token(self):
        """Direct token should be returned as-is."""
        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo",
            token="ghp_directtoken123",
        )

        token = _get_github_token(source)
        assert token == "ghp_directtoken123"

    def test_fallback_to_github_token(self):
        """Without source token, should fall back to GITHUB_TOKEN."""
        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo",
            # No token field
        )

        with patch.dict(os.environ, {"GITHUB_TOKEN": "global_github_token"}):
            token = _get_github_token(source)
            assert token == "global_github_token"

    def test_fallback_to_gh_token(self):
        """Without GITHUB_TOKEN, should fall back to GH_TOKEN."""
        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo",
        )

        with patch.dict(os.environ, {"GH_TOKEN": "global_gh_token"}, clear=True):
            token = _get_github_token(source)
            assert token == "global_gh_token"

    def test_no_token_available(self):
        """With no tokens, should return None."""
        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo",
        )

        with patch.dict(os.environ, {}, clear=True):
            token = _get_github_token(source)
            assert token is None

    def test_priority_source_over_global(self):
        """Source token should take priority over global tokens."""
        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo",
            token="$SOURCE_TOKEN",
        )

        with patch.dict(
            os.environ,
            {
                "SOURCE_TOKEN": "source_specific",
                "GITHUB_TOKEN": "global_github",
                "GH_TOKEN": "global_gh",
            },
        ):
            token = _get_github_token(source)
            assert token == "source_specific"


class TestTokenUsageInGitOperations:
    """Test that tokens are used in Git operations."""

    @patch("requests.get")
    def test_tree_api_uses_source_token(self, mock_get, tmp_path):
        """GitHub Tree API should use source-specific token."""
        from claude_mpm.services.skills.git_skill_source_manager import (
            GitSkillSourceManager,
        )

        # Mock successful API responses
        mock_refs_response = Mock()
        mock_refs_response.status_code = 200
        mock_refs_response.json.return_value = {"object": {"sha": "abc123"}}

        mock_tree_response = Mock()
        mock_tree_response.status_code = 200
        mock_tree_response.json.return_value = {
            "tree": [{"type": "blob", "path": "test.md"}]
        }

        mock_get.side_effect = [mock_refs_response, mock_tree_response]

        # Create config with source
        config_path = tmp_path / "skill_sources.yaml"
        config = SkillSourceConfiguration(config_path=config_path)

        source = SkillSource(
            id="test",
            type="git",
            url="https://github.com/owner/repo",
            token="$SOURCE_TOKEN",
        )
        config.save([source])

        manager = GitSkillSourceManager(config, cache_dir=tmp_path / "cache")

        with patch.dict(os.environ, {"SOURCE_TOKEN": "my_source_token"}):
            manager._discover_repository_files_via_tree_api(
                "owner/repo", "main", source
            )

            # Verify token was used in requests
            calls = mock_get.call_args_list
            assert len(calls) >= 1

            # Check first call (refs API)
            headers = calls[0][1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "token my_source_token"
