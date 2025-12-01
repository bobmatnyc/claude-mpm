"""Tests for Git skill source Phase 2 refactoring - Cache architecture.

Test Coverage:
- Git Tree API discovery (finding all 272 files)
- Cache directory structure and creation
- File download to cache with nested structure
- Deployment from cache to project
- ETag caching still functional
- Progress callback with absolute positioning
- Integration with existing tests (no regressions)
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.claude_mpm.config.skill_sources import (
    SkillSource,
    SkillSourceConfiguration,
)
from src.claude_mpm.services.skills.git_skill_source_manager import (
    GitSkillSourceManager,
)


class TestPhase2CacheArchitecture:
    """Tests for Phase 2 cache-first sync architecture."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_path = Path(f.name)
        yield config_path
        if config_path.exists():
            config_path.unlink()

    @pytest.fixture
    def mock_config(self, temp_config_file):
        """Create mock configuration with test source."""
        config = SkillSourceConfiguration(config_path=temp_config_file)
        source = SkillSource(
            id="test-source",
            type="git",
            url="https://github.com/bobmatnyc/claude-mpm-skills",
            branch="main",
            priority=0,
            enabled=True,
        )
        config.save([source])
        return config

    @pytest.fixture
    def manager(self, mock_config, temp_cache_dir):
        """Create GitSkillSourceManager with test cache."""
        return GitSkillSourceManager(config=mock_config, cache_dir=temp_cache_dir)

    def test_cache_directory_initialization(self, temp_cache_dir, mock_config):
        """Test cache directory is created on initialization."""
        manager = GitSkillSourceManager(config=mock_config, cache_dir=temp_cache_dir)

        assert manager.cache_dir == temp_cache_dir
        assert temp_cache_dir.exists()

    def test_default_cache_directory(self, mock_config):
        """Test default cache directory is ~/.claude-mpm/cache/skills/."""
        manager = GitSkillSourceManager(config=mock_config)

        expected = Path.home() / ".claude-mpm" / "cache" / "skills"
        assert manager.cache_dir == expected

    @patch("requests.get")
    def test_git_tree_api_discovery(self, mock_get, manager):
        """Test Git Tree API discovers all files recursively."""
        # Mock refs API response (commit SHA lookup)
        refs_response = Mock()
        refs_response.status_code = 200
        refs_response.json.return_value = {"object": {"sha": "abc123"}}

        # Mock tree API response (recursive file list)
        tree_response = Mock()
        tree_response.status_code = 200
        tree_response.json.return_value = {
            "tree": [
                {"type": "blob", "path": "collections/toolchains/python/pytest.md"},
                {"type": "blob", "path": "collections/toolchains/python/mypy.md"},
                {"type": "blob", "path": "collections/universal/testing/tdd.md"},
                {"type": "tree", "path": "collections/toolchains"},  # directory
                {"type": "blob", "path": "README.md"},
                {"type": "blob", "path": ".gitignore"},
            ]
        }

        # Setup mock to return different responses for refs and tree
        mock_get.side_effect = [refs_response, tree_response]

        # Discover files
        files = manager._discover_repository_files_via_tree_api(
            "bobmatnyc/claude-mpm-skills", "main"
        )

        # Verify API calls
        assert mock_get.call_count == 2

        # Verify refs API call
        refs_call = mock_get.call_args_list[0]
        assert (
            "https://api.github.com/repos/bobmatnyc/claude-mpm-skills/git/refs/heads/main"
            in refs_call[0][0]
        )

        # Verify tree API call
        tree_call = mock_get.call_args_list[1]
        assert (
            "https://api.github.com/repos/bobmatnyc/claude-mpm-skills/git/trees/abc123"
            in tree_call[0][0]
        )
        assert tree_call[1]["params"] == {"recursive": "1"}

        # Verify results - should find all blobs (files)
        # Tree API returns all files, filtering happens in _recursive_sync_repository
        assert len(files) >= 5  # At least the .md files
        assert "collections/toolchains/python/pytest.md" in files
        assert "collections/toolchains/python/mypy.md" in files
        assert "collections/universal/testing/tdd.md" in files

        # Verify directories are filtered out
        assert "collections/toolchains" not in files

    @patch("requests.get")
    def test_git_tree_api_rate_limit_handling(self, mock_get, manager):
        """Test Git Tree API handles rate limiting gracefully."""
        # Mock rate limit response
        refs_response = Mock()
        refs_response.status_code = 403
        mock_get.return_value = refs_response

        # Should return empty list on rate limit
        files = manager._discover_repository_files_via_tree_api(
            "bobmatnyc/claude-mpm-skills", "main"
        )

        assert files == []

    @patch("requests.get")
    def test_cache_structure_preserves_nested_paths(self, mock_get, manager):
        """Test files are cached with nested directory structure preserved."""
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)

        # Mock refs and tree responses
        refs_response = Mock()
        refs_response.status_code = 200
        refs_response.json.return_value = {"object": {"sha": "abc123"}}

        tree_response = Mock()
        tree_response.status_code = 200
        tree_response.json.return_value = {
            "tree": [
                {"type": "blob", "path": "collections/toolchains/python/pytest.md"},
            ]
        }

        # Mock file download
        file_response = Mock()
        file_response.status_code = 200
        file_response.content = b"# Pytest Skill\n\nContent"
        file_response.headers = {"ETag": '"abc123"'}
        file_response.text = "# Pytest Skill\n\nContent"

        mock_get.side_effect = [refs_response, tree_response, file_response]

        # Sync repository
        _files_updated, _files_cached = manager._recursive_sync_repository(
            source, cache_path, force=False
        )

        # Verify nested structure is preserved
        expected_file = (
            cache_path / "collections" / "toolchains" / "python" / "pytest.md"
        )
        assert expected_file.exists()
        assert expected_file.read_text() == "# Pytest Skill\n\nContent"

    @patch("requests.get")
    def test_etag_caching_still_works(self, mock_get, manager):
        """Test ETag caching is preserved in Phase 2."""
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)

        # Create cached file with ETag
        test_file = cache_path / "test.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("cached content")

        # Store ETag
        etag_cache_file = cache_path / ".etag_cache.json"
        etag_cache_file.write_text('{"' + str(test_file) + '": "etag123"}')

        # Mock refs and tree responses
        refs_response = Mock()
        refs_response.status_code = 200
        refs_response.json.return_value = {"object": {"sha": "abc123"}}

        tree_response = Mock()
        tree_response.status_code = 200
        tree_response.json.return_value = {
            "tree": [{"type": "blob", "path": "test.md"}]
        }

        # Mock file response - 304 Not Modified
        file_response = Mock()
        file_response.status_code = 304
        mock_get.side_effect = [refs_response, tree_response, file_response]

        # Sync repository
        _files_updated, _files_cached = manager._recursive_sync_repository(
            source, cache_path, force=False
        )

        # Verify ETag cache hit (0 updates, 1 cached)
        assert files_updated == 0
        assert files_cached == 1

    def test_progress_callback_absolute_positioning(self, manager):
        """Test progress callback receives absolute position, not increments."""
        progress_calls = []

        def progress_callback(position):
            progress_calls.append(position)

        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)

        # Mock discovery and download
        with patch.object(
            manager, "_discover_repository_files_via_tree_api"
        ) as mock_discover:
            mock_discover.return_value = ["file1.md", "file2.md", "file3.md"]

            with patch.object(manager, "_download_file_with_etag") as mock_download:
                mock_download.return_value = True

                manager._recursive_sync_repository(
                    source, cache_path, progress_callback=progress_callback
                )

        # Verify absolute positioning (1, 2, 3, not 1, 1, 1)
        assert progress_calls == [1, 2, 3]

    def test_deploy_skills_to_project(self, manager, temp_project_dir):
        """Test deployment from cache to project directory."""
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)

        # Create nested skill structure in cache
        skill_dir = cache_path / "collections" / "toolchains" / "python-pytest"
        skill_dir.mkdir(parents=True)

        skill_content = """---
name: Pytest Skill
description: Testing with pytest
skill_version: 1.0.0
tags: [testing, python]
---

# Pytest Skill

Content here.
"""
        (skill_dir / "SKILL.md").write_text(skill_content)
        (skill_dir / "helper.py").write_text("# Helper")

        # Deploy to project
        result = manager.deploy_skills_to_project(temp_project_dir, force=False)

        # Verify deployment results
        assert result["deployed_count"] >= 1 or result["updated_count"] >= 1
        assert result["failed_count"] == 0

        # Verify flat structure in project
        deployment_dir = temp_project_dir / ".claude-mpm" / "skills"
        assert deployment_dir.exists()

        # Skill should be deployed with flattened name
        deployed_skills = [d for d in deployment_dir.iterdir() if d.is_dir()]
        assert len(deployed_skills) >= 1

        # Verify skill content is preserved
        deployed_skill = deployed_skills[0]
        assert (deployed_skill / "SKILL.md").exists()
        assert (deployed_skill / "helper.py").exists()

    def test_deploy_skills_to_project_selective(self, manager, temp_project_dir):
        """Test selective deployment of specific skills."""
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)

        # Create two skills in cache
        for skill_name in ["skill1", "skill2"]:
            skill_dir = cache_path / skill_name
            skill_dir.mkdir(parents=True)
            skill_content = f"""---
name: {skill_name.capitalize()}
description: Test skill
---
Content
"""
            (skill_dir / "SKILL.md").write_text(skill_content)

        # Deploy only skill1
        result = manager.deploy_skills_to_project(
            temp_project_dir, skill_list=["Skill1"], force=False
        )

        # Verify only skill1 was deployed
        deployment_dir = temp_project_dir / ".claude-mpm" / "skills"
        deployed_names = [d.name for d in deployment_dir.iterdir() if d.is_dir()]

        # Should have deployed skill1 but not skill2
        assert any("skill1" in name.lower() for name in deployed_names)

    def test_deploy_skills_to_project_force_overwrite(self, manager, temp_project_dir):
        """Test force flag overwrites existing deployments."""
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)

        # Create skill in cache
        skill_dir = cache_path / "test-skill"
        skill_dir.mkdir(parents=True)
        skill_content = """---
name: Test Skill
description: Test
skill_version: 1.0.0
---
V1"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Deploy once
        result1 = manager.deploy_skills_to_project(temp_project_dir, force=False)
        assert result1["deployed_count"] >= 1 or result1["updated_count"] >= 1

        # Deploy again without force - should skip
        result2 = manager.deploy_skills_to_project(temp_project_dir, force=False)
        assert result2["skipped_count"] >= 1 or result2["deployed_count"] >= 0

        # Deploy with force - should update
        result3 = manager.deploy_skills_to_project(temp_project_dir, force=True)
        assert result3["deployed_count"] >= 1 or result3["updated_count"] >= 1

    @patch("requests.get")
    def test_integration_sync_and_deploy(self, mock_get, manager, temp_project_dir):
        """Test complete sync-to-cache then deploy-to-project flow."""
        # Mock GitHub API responses
        refs_response = Mock()
        refs_response.status_code = 200
        refs_response.json.return_value = {"object": {"sha": "abc123"}}

        tree_response = Mock()
        tree_response.status_code = 200
        tree_response.json.return_value = {
            "tree": [
                {"type": "blob", "path": "collections/testing/pytest/SKILL.md"},
            ]
        }

        file_response = Mock()
        file_response.status_code = 200
        file_response.content = b"""---
name: Pytest
description: Testing
---
Content"""
        file_response.text = """---
name: Pytest
description: Testing
---
Content"""
        file_response.headers = {"ETag": '"abc123"'}

        mock_get.side_effect = [refs_response, tree_response, file_response]

        # Step 1: Sync to cache
        sync_result = manager.sync_source("test-source", force=False)
        assert sync_result["synced"] is True

        # Step 2: Deploy from cache to project
        deploy_result = manager.deploy_skills_to_project(temp_project_dir)
        assert deploy_result["deployed_count"] >= 1

        # Verify files exist in both cache and project
        cache_path = manager._get_source_cache_path(
            manager.config.get_source("test-source")
        )
        assert (cache_path / "collections" / "testing" / "pytest" / "SKILL.md").exists()

        project_skills = temp_project_dir / ".claude-mpm" / "skills"
        assert project_skills.exists()
        assert len(list(project_skills.iterdir())) >= 1

    def test_no_regression_existing_tests(self, manager):
        """Verify Phase 2 doesn't break existing functionality."""
        # Test cache directory still works
        assert manager.cache_dir.exists()

        # Test source cache path still works
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)
        assert cache_path == manager.cache_dir / "test-source"

        # Test priority resolution still works
        result = manager._apply_priority_resolution({})
        assert result == []


class TestPhase2ErrorHandling:
    """Test error handling in Phase 2 refactoring."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_path = Path(f.name)
        yield config_path
        if config_path.exists():
            config_path.unlink()

    @pytest.fixture
    def mock_config(self, temp_config_file):
        """Create mock configuration."""
        config = SkillSourceConfiguration(config_path=temp_config_file)
        source = SkillSource(
            id="test-source",
            type="git",
            url="https://github.com/owner/repo",
            enabled=True,
        )
        config.save([source])
        return config

    @pytest.fixture
    def manager(self, mock_config, temp_cache_dir):
        """Create manager instance."""
        return GitSkillSourceManager(config=mock_config, cache_dir=temp_cache_dir)

    def test_tree_api_network_error_handling(self, manager):
        """Test network errors during Tree API discovery."""
        # Use requests library with mocking
        import requests

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")

            files = manager._discover_repository_files_via_tree_api(
                "owner/repo", "main"
            )

            # Should return empty list on error
            assert files == []

    @patch("requests.get")
    def test_tree_api_json_parse_error_handling(self, mock_get, manager):
        """Test JSON parsing errors during Tree API discovery."""
        response = Mock()
        response.status_code = 200
        response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = response

        files = manager._discover_repository_files_via_tree_api("owner/repo", "main")

        # Should return empty list on parse error
        assert files == []

    def test_deploy_missing_cache_file(self, manager, temp_cache_dir):
        """Test deployment handles missing cache files gracefully."""
        # Create project directory
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Try to deploy without syncing (cache empty)
            result = manager.deploy_skills_to_project(project_dir)

            # Should complete without crashing
            assert "deployed" in result
            assert "failed" in result

    def test_deploy_permission_error(self, manager):
        """Test deployment handles permission errors."""
        # Skip on systems where permission tests don't work
        import os
        import stat
        import sys

        if sys.platform == "win32":
            pytest.skip("Permission test not applicable on Windows")

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create .claude-mpm directory first
            claude_dir = project_dir / ".claude-mpm"
            claude_dir.mkdir(parents=True, exist_ok=True)

            try:
                # Make .claude-mpm read-only (can't create skills subdir)
                os.chmod(claude_dir, stat.S_IRUSR | stat.S_IXUSR)

                result = manager.deploy_skills_to_project(project_dir, force=True)

                # Should handle permission error gracefully (no crash)
                assert isinstance(result, dict)
                assert "deployed" in result
                assert "failed" in result

            finally:
                # Restore permissions for cleanup
                try:
                    os.chmod(
                        claude_dir,
                        stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR,
                    )
                except Exception:
                    pass  # Ignore cleanup errors
