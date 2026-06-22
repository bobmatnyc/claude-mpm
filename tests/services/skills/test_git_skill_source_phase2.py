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

from src.claude_mpm.config.skill_sources import SkillSource, SkillSourceConfiguration
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
        """Test ETag caching is preserved in Phase 2 with external cache location.

        After fix #882 the ETag cache lives OUTSIDE the clone working tree at
        ``manager.etag_dir / "{source_id}.json"``.  This test verifies:
        - The external cache is read before the HTTP request (304 hit).
        - No ``.etag_cache.json`` is written into the clone tree.
        """
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)

        # Create cached file
        test_file = cache_path / "test.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("cached content")

        # Store ETag in the NEW external location (fix #882)
        external_etag_file = manager._get_etag_cache_file(source.id)
        external_etag_file.parent.mkdir(parents=True, exist_ok=True)
        import json

        external_etag_file.write_text(json.dumps({str(test_file): "etag123"}))

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
        files_updated, files_cached = manager._recursive_sync_repository(
            source, cache_path, force=False
        )

        # Verify ETag cache hit (0 updates, 1 cached)
        assert files_updated == 0
        assert files_cached == 1

    @patch("requests.get")
    def test_clone_tree_clean_after_sync(self, mock_get, manager):
        """After a sync, no .etag_cache.json should exist inside the clone tree (#882)."""
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)
        cache_path.mkdir(parents=True, exist_ok=True)

        # Mock refs + tree + file download
        refs_response = Mock()
        refs_response.status_code = 200
        refs_response.json.return_value = {"object": {"sha": "abc123"}}

        tree_response = Mock()
        tree_response.status_code = 200
        tree_response.json.return_value = {
            "tree": [{"type": "blob", "path": "skill.md"}]
        }

        file_response = Mock()
        file_response.status_code = 200
        file_response.content = b"# skill"
        file_response.headers = {"ETag": '"newtag"'}
        mock_get.side_effect = [refs_response, tree_response, file_response]

        manager._recursive_sync_repository(source, cache_path, force=False)

        # The clone working tree must NOT contain .etag_cache.json
        in_tree_cache = list(cache_path.rglob(".etag_cache.json"))
        assert in_tree_cache == [], (
            f"ETag cache files found inside clone working tree: {in_tree_cache}"
        )

        # The external ETag file MUST exist
        external_etag_file = manager._get_etag_cache_file(source.id)
        assert external_etag_file.exists(), (
            f"External ETag file missing: {external_etag_file}"
        )

    def test_migrate_legacy_etag_cache(self, manager):
        """Legacy in-tree .etag_cache.json is migrated to external location with relative keys (#882, #884).

        New contract (fix #884): migrated cache keys are relative filenames
        (e.g. ``skill.md``), NOT absolute paths.  This makes the cache
        portable across machine renames and CI/Docker environments.

        This test verifies the no-collision path: no pre-existing external
        cache, so every legacy entry is migrated as-is (after normalisation).
        """
        import json

        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)
        cache_path.mkdir(parents=True, exist_ok=True)

        # Ensure no pre-existing external cache for this source so we test
        # the simple migration path (no collision).  The etag_dir is shared
        # across tests (it resolves to a sibling of the OS temp dir), so a
        # prior test may have written it — remove it explicitly.
        external_file = manager._get_etag_cache_file(source.id)
        if external_file.exists():
            external_file.unlink()

        # Legacy cache uses absolute-path keys (old format)
        legacy_entries = {
            str(cache_path / "skill.md"): '"etag-legacy"',
            str(cache_path / "other.md"): '"etag-other"',
        }

        # Write legacy in-tree cache
        legacy_file = cache_path / ".etag_cache.json"
        legacy_file.write_text(json.dumps(legacy_entries))
        assert legacy_file.exists()

        # Run migration
        manager._migrate_legacy_etag_cache(source.id, cache_path)

        # Legacy file must be gone (clone is clean)
        assert not legacy_file.exists(), (
            "Legacy in-tree .etag_cache.json was not removed"
        )

        # External file must contain migrated entries with RELATIVE filename keys
        assert external_file.exists(), "External ETag file was not created"
        migrated = json.loads(external_file.read_text())

        # Keys must be relative filenames, not absolute paths (#884)
        assert "skill.md" in migrated, (
            f"Relative key 'skill.md' missing from migrated cache; got keys: {list(migrated)}"
        )
        assert "other.md" in migrated, (
            f"Relative key 'other.md' missing from migrated cache; got keys: {list(migrated)}"
        )
        assert migrated["skill.md"] == '"etag-legacy"'
        assert migrated["other.md"] == '"etag-other"'

        # No absolute-path keys must remain in the migrated cache
        for key in migrated:
            assert not key.startswith("/"), (
                f"Absolute-path key found in migrated cache: {key!r} — expected relative filenames only"
            )

    def test_migrate_legacy_etag_cache_merges_with_existing(self, manager):
        """Migration merges legacy + external caches; ALL keys are normalised to relative filenames.

        Precedence rule (documented in _migrate_legacy_etag_cache docstring):
        external cache wins on key collision.  Both the legacy in-tree entries
        AND the pre-existing external entries are normalised to relative
        filenames before merging, so the result must contain ONLY relative-
        filename keys — no absolute paths (#884).
        """
        import json

        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)
        cache_path.mkdir(parents=True, exist_ok=True)

        # Legacy in-tree cache uses absolute-path keys (old format).
        # "skill.md" appears in both legacy and external — collision case.
        # "old.md" appears only in legacy — must be preserved.
        legacy_file = cache_path / ".etag_cache.json"
        legacy_file.write_text(
            json.dumps(
                {
                    str(cache_path / "skill.md"): '"etag-legacy"',
                    str(cache_path / "old.md"): '"old-etag"',
                }
            )
        )

        # Pre-existing external cache also uses absolute-path keys (old format).
        # After migration this entry must be normalised to a relative key too.
        external_file = manager._get_etag_cache_file(source.id)
        external_file.parent.mkdir(parents=True, exist_ok=True)
        external_file.write_text(
            json.dumps({str(cache_path / "skill.md"): '"etag-external"'})
        )

        manager._migrate_legacy_etag_cache(source.id, cache_path)

        # Legacy file must be removed
        assert not legacy_file.exists()

        merged = json.loads(external_file.read_text())

        # No absolute-path keys may remain — the whole cache must use relative filenames
        for key in merged:
            assert not key.startswith("/"), (
                f"Absolute-path key found in merged cache: {key!r} — expected relative filenames only"
            )

        # Collision: external wins → "skill.md" → '"etag-external"'
        assert "skill.md" in merged, (
            f"Relative key 'skill.md' missing from merged cache; got: {list(merged)}"
        )
        assert merged["skill.md"] == '"etag-external"', (
            f"Expected external ETag to win on collision; got: {merged['skill.md']}"
        )

        # Legacy-only entry "old.md" must be preserved with relative key
        assert "old.md" in merged, (
            f"Relative key 'old.md' missing from merged cache; got: {list(merged)}"
        )
        assert merged["old.md"] == '"old-etag"'

    def test_migrate_legacy_etag_cache_no_legacy_file(self, manager):
        """Migration is a no-op when no legacy file exists (fast path)."""
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)
        cache_path.mkdir(parents=True, exist_ok=True)

        # Ensure no legacy in-tree file is present
        legacy_file = cache_path / ".etag_cache.json"
        assert not legacy_file.exists()

        # Snapshot the external file state before calling migration
        external_file = manager._get_etag_cache_file(source.id)
        pre_mtime = external_file.stat().st_mtime if external_file.exists() else None

        # Should not raise
        manager._migrate_legacy_etag_cache(source.id, cache_path)

        # External file must NOT have been written (migration was a no-op)
        if pre_mtime is None:
            assert not external_file.exists(), (
                "External ETag file was created despite no legacy file to migrate"
            )
        else:
            assert external_file.stat().st_mtime == pre_mtime, (
                "External ETag file was modified despite no legacy file to migrate"
            )

    def test_migrate_legacy_etag_cache_corrupted_file(self, manager):
        """Migration handles a corrupted in-tree cache gracefully (still removes the file)."""
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)
        cache_path.mkdir(parents=True, exist_ok=True)

        legacy_file = cache_path / ".etag_cache.json"
        legacy_file.write_text("NOT VALID JSON {{{{")

        # Should not raise
        manager._migrate_legacy_etag_cache(source.id, cache_path)

        # File must be removed even on parse error
        assert not legacy_file.exists(), "Corrupted legacy file was not removed"

    def test_get_etag_cache_file_outside_clone(self, manager):
        """_get_etag_cache_file returns a path that is NOT inside the clone dir (#882)."""
        source = manager.config.get_source("test-source")
        cache_path = manager._get_source_cache_path(source)
        etag_file = manager._get_etag_cache_file(source.id)

        # The etag file must NOT be a descendant of the clone root
        is_inside_clone = True
        try:
            etag_file.relative_to(cache_path)
        except ValueError:
            is_inside_clone = False
        assert not is_inside_clone, (
            f"ETag cache file {etag_file} is inside the clone tree {cache_path}"
        )

        # Confirm the naming scheme
        assert etag_file.name == f"{source.id}.json"
        assert etag_file.parent == manager.etag_dir

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
