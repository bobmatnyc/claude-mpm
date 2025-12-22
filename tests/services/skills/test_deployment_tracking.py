"""Tests for skill deployment tracking and orphan cleanup.

WHY: Ensures deployment tracking index correctly records deployed skills
and cleanup correctly identifies and removes orphaned skills.

DESIGN DECISIONS:
- Test index file creation, loading, and saving
- Test skill tracking and untracking operations
- Test orphan cleanup logic with various scenarios
- Mock file system operations where appropriate
- Validate security constraints (path traversal prevention)
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.skills.selective_skill_deployer import (
    DEPLOYED_INDEX_FILE,
    cleanup_orphan_skills,
    load_deployment_index,
    save_deployment_index,
    track_deployed_skill,
    untrack_skill,
)


class TestLoadDeploymentIndex:
    """Test loading deployment tracking index."""

    def test_load_existing_index(self, tmp_path):
        """Test loading valid existing index file."""
        index_data = {
            "deployed_skills": {
                "skill-a": {"collection": "claude-mpm", "deployed_at": "2025-12-22T10:00:00Z"},
                "skill-b": {"collection": "obra", "deployed_at": "2025-12-22T11:00:00Z"},
            },
            "last_sync": "2025-12-22T11:30:00Z",
            "user_requested_skills": [],
        }

        # Create index file
        index_path = tmp_path / DEPLOYED_INDEX_FILE
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f)

        # Load index
        result = load_deployment_index(tmp_path)

        assert result == index_data
        assert len(result["deployed_skills"]) == 2
        assert "skill-a" in result["deployed_skills"]
        assert result["last_sync"] == "2025-12-22T11:30:00Z"

    def test_load_nonexistent_index(self, tmp_path):
        """Test loading when index file doesn't exist."""
        result = load_deployment_index(tmp_path)

        # Should return default empty index (includes user_requested_skills)
        assert result == {"deployed_skills": {}, "last_sync": None, "user_requested_skills": []}

    def test_load_corrupted_index(self, tmp_path):
        """Test loading corrupted JSON file."""
        index_path = tmp_path / DEPLOYED_INDEX_FILE
        index_path.write_text("not valid json{{{")

        result = load_deployment_index(tmp_path)

        # Should return default empty index on error (includes user_requested_skills)
        assert result == {"deployed_skills": {}, "last_sync": None, "user_requested_skills": []}

    def test_load_index_missing_keys(self, tmp_path):
        """Test loading index with missing keys."""
        # Create index with only one key
        index_path = tmp_path / DEPLOYED_INDEX_FILE
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({"deployed_skills": {"skill-a": {}}}, f)

        result = load_deployment_index(tmp_path)

        # Should add missing keys
        assert "deployed_skills" in result
        assert "last_sync" in result
        assert result["last_sync"] is None


class TestSaveDeploymentIndex:
    """Test saving deployment tracking index."""

    def test_save_index(self, tmp_path):
        """Test saving index to file."""
        index = {
            "deployed_skills": {
                "skill-a": {"collection": "claude-mpm", "deployed_at": "2025-12-22T10:00:00Z"}
            },
            "last_sync": "2025-12-22T10:00:00Z",
        }

        save_deployment_index(tmp_path, index)

        # Verify file was created
        index_path = tmp_path / DEPLOYED_INDEX_FILE
        assert index_path.exists()

        # Verify content
        with open(index_path, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data == index

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates parent directory if it doesn't exist."""
        nested_path = tmp_path / "nested" / "path"
        index = {"deployed_skills": {}, "last_sync": None}

        save_deployment_index(nested_path, index)

        # Verify directory was created
        assert nested_path.exists()
        assert (nested_path / DEPLOYED_INDEX_FILE).exists()

    def test_save_overwrites_existing(self, tmp_path):
        """Test that save overwrites existing index."""
        # Create initial index
        initial = {"deployed_skills": {"skill-old": {}}, "last_sync": "old"}
        save_deployment_index(tmp_path, initial)

        # Save new index
        updated = {"deployed_skills": {"skill-new": {}}, "last_sync": "new"}
        save_deployment_index(tmp_path, updated)

        # Verify updated content
        result = load_deployment_index(tmp_path)
        assert "skill-new" in result["deployed_skills"]
        assert "skill-old" not in result["deployed_skills"]
        assert result["last_sync"] == "new"


class TestTrackDeployedSkill:
    """Test tracking individual skill deployments."""

    def test_track_new_skill(self, tmp_path):
        """Test tracking a new skill deployment."""
        with patch("claude_mpm.services.skills.selective_skill_deployer.datetime") as mock_dt:
            mock_dt.utcnow.return_value.isoformat.return_value = "2025-12-22T10:00:00"

            track_deployed_skill(tmp_path, "test-skill", "claude-mpm")

            # Verify index was created with skill
            index = load_deployment_index(tmp_path)
            assert "test-skill" in index["deployed_skills"]
            assert index["deployed_skills"]["test-skill"]["collection"] == "claude-mpm"
            assert index["deployed_skills"]["test-skill"]["deployed_at"] == "2025-12-22T10:00:00Z"
            assert index["last_sync"] == "2025-12-22T10:00:00Z"

    def test_track_multiple_skills(self, tmp_path):
        """Test tracking multiple skills."""
        track_deployed_skill(tmp_path, "skill-a", "collection-1")
        track_deployed_skill(tmp_path, "skill-b", "collection-2")
        track_deployed_skill(tmp_path, "skill-c", "collection-1")

        index = load_deployment_index(tmp_path)
        assert len(index["deployed_skills"]) == 3
        assert "skill-a" in index["deployed_skills"]
        assert "skill-b" in index["deployed_skills"]
        assert "skill-c" in index["deployed_skills"]

    def test_track_overwrites_existing(self, tmp_path):
        """Test tracking same skill again updates metadata."""
        # First deployment
        with patch("claude_mpm.services.skills.selective_skill_deployer.datetime") as mock_dt:
            mock_dt.utcnow.return_value.isoformat.return_value = "2025-12-22T10:00:00"
            track_deployed_skill(tmp_path, "test-skill", "old-collection")

        # Second deployment
        with patch("claude_mpm.services.skills.selective_skill_deployer.datetime") as mock_dt:
            mock_dt.utcnow.return_value.isoformat.return_value = "2025-12-22T11:00:00"
            track_deployed_skill(tmp_path, "test-skill", "new-collection")

        index = load_deployment_index(tmp_path)
        assert index["deployed_skills"]["test-skill"]["collection"] == "new-collection"
        assert index["deployed_skills"]["test-skill"]["deployed_at"] == "2025-12-22T11:00:00Z"


class TestUntrackSkill:
    """Test removing skill from tracking index."""

    def test_untrack_existing_skill(self, tmp_path):
        """Test untracking a tracked skill."""
        # Track some skills
        track_deployed_skill(tmp_path, "skill-a", "collection")
        track_deployed_skill(tmp_path, "skill-b", "collection")

        # Untrack one
        untrack_skill(tmp_path, "skill-a")

        # Verify removal
        index = load_deployment_index(tmp_path)
        assert "skill-a" not in index["deployed_skills"]
        assert "skill-b" in index["deployed_skills"]

    def test_untrack_nonexistent_skill(self, tmp_path):
        """Test untracking skill that isn't tracked."""
        # Track one skill
        track_deployed_skill(tmp_path, "skill-a", "collection")

        # Untrack different skill (should not error)
        untrack_skill(tmp_path, "skill-b")

        # Verify index unchanged
        index = load_deployment_index(tmp_path)
        assert "skill-a" in index["deployed_skills"]

    def test_untrack_updates_last_sync(self, tmp_path):
        """Test that untrack updates last_sync timestamp."""
        track_deployed_skill(tmp_path, "skill-a", "collection")

        with patch("claude_mpm.services.skills.selective_skill_deployer.datetime") as mock_dt:
            mock_dt.utcnow.return_value.isoformat.return_value = "2025-12-22T12:00:00"
            untrack_skill(tmp_path, "skill-a")

        index = load_deployment_index(tmp_path)
        assert index["last_sync"] == "2025-12-22T12:00:00Z"


class TestCleanupOrphanSkills:
    """Test orphaned skill cleanup logic."""

    def test_cleanup_removes_orphaned_skills(self, tmp_path):
        """Test cleanup removes skills not in required set."""
        # Setup: Create skill directories
        (tmp_path / "skill-a").mkdir()
        (tmp_path / "skill-b").mkdir()
        (tmp_path / "skill-c").mkdir()

        # Track all skills
        track_deployed_skill(tmp_path, "skill-a", "collection")
        track_deployed_skill(tmp_path, "skill-b", "collection")
        track_deployed_skill(tmp_path, "skill-c", "collection")

        # Cleanup: only skill-a and skill-b are required
        required = {"skill-a", "skill-b"}
        result = cleanup_orphan_skills(tmp_path, required)

        # Verify skill-c was removed
        assert result["removed_count"] == 1
        assert "skill-c" in result["removed_skills"]
        assert result["kept_count"] == 2

        # Verify directory was deleted
        assert not (tmp_path / "skill-c").exists()
        assert (tmp_path / "skill-a").exists()
        assert (tmp_path / "skill-b").exists()

        # Verify index was updated
        index = load_deployment_index(tmp_path)
        assert "skill-c" not in index["deployed_skills"]
        assert "skill-a" in index["deployed_skills"]
        assert "skill-b" in index["deployed_skills"]

    def test_cleanup_no_orphaned_skills(self, tmp_path):
        """Test cleanup when all tracked skills are required."""
        # Setup
        (tmp_path / "skill-a").mkdir()
        (tmp_path / "skill-b").mkdir()
        track_deployed_skill(tmp_path, "skill-a", "collection")
        track_deployed_skill(tmp_path, "skill-b", "collection")

        # Cleanup: all tracked skills are required
        required = {"skill-a", "skill-b"}
        result = cleanup_orphan_skills(tmp_path, required)

        # Verify no removals
        assert result["removed_count"] == 0
        assert result["removed_skills"] == []
        assert result["kept_count"] == 2

    def test_cleanup_handles_missing_directories(self, tmp_path):
        """Test cleanup when tracked skill directory doesn't exist."""
        # Track skill without creating directory
        track_deployed_skill(tmp_path, "ghost-skill", "collection")

        # Cleanup
        required = set()
        result = cleanup_orphan_skills(tmp_path, required)

        # Should still untrack even though directory doesn't exist
        assert result["removed_count"] == 0  # No directory to remove
        index = load_deployment_index(tmp_path)
        assert "ghost-skill" not in index["deployed_skills"]

    def test_cleanup_handles_symlinks(self, tmp_path):
        """Test cleanup handles symlink skills correctly."""
        # Create a real directory and symlink to it
        real_dir = tmp_path / "real_skill"
        real_dir.mkdir()
        symlink = tmp_path / "symlink-skill"
        symlink.symlink_to(real_dir)

        track_deployed_skill(tmp_path, "symlink-skill", "collection")

        # Cleanup
        required = set()
        result = cleanup_orphan_skills(tmp_path, required)

        # Symlink should be removed
        assert not symlink.exists()
        # Real directory should still exist
        assert real_dir.exists()

    def test_cleanup_path_traversal_protection(self, tmp_path):
        """Test cleanup prevents path traversal attacks."""
        # Setup: Create directory outside claude_skills_dir
        parent_dir = tmp_path.parent / "outside"
        parent_dir.mkdir(exist_ok=True)
        outside_file = parent_dir / "evil.txt"
        outside_file.write_text("should not be deleted")

        # Create symlink that points outside
        evil_symlink = tmp_path / "..%2F..%2Fevil"  # URL-encoded path traversal
        if not evil_symlink.exists():
            try:
                evil_symlink.symlink_to(outside_file)
            except OSError:
                # Skip test if symlink creation fails
                pytest.skip("Cannot create symlink on this platform")

        # Manually add to index (bypassing normal tracking)
        index = load_deployment_index(tmp_path)
        index["deployed_skills"]["..%2F..%2Fevil"] = {
            "collection": "malicious",
            "deployed_at": "2025-12-22T10:00:00Z",
        }
        save_deployment_index(tmp_path, index)

        # Cleanup should handle safely
        required = set()
        result = cleanup_orphan_skills(tmp_path, required)

        # Should have error for path traversal attempt OR skip the skill
        # The implementation may either error or skip, both are acceptable
        if evil_symlink.resolve() != (tmp_path / "..%2F..%2Fevil").resolve():
            # If symlink points outside, should either error or skip
            assert result["removed_count"] == 0 or len(result["errors"]) > 0

        # Outside file should not be deleted
        assert outside_file.exists()

    def test_cleanup_handles_removal_errors(self, tmp_path):
        """Test cleanup gracefully handles removal errors."""
        # Create skill directory with restricted permissions
        skill_dir = tmp_path / "locked-skill"
        skill_dir.mkdir()
        track_deployed_skill(tmp_path, "locked-skill", "collection")

        # Mock shutil.rmtree to raise an error
        # Need to patch in the cleanup_orphan_skills function's scope
        import shutil
        original_rmtree = shutil.rmtree

        def mock_rmtree(path, *args, **kwargs):
            if "locked-skill" in str(path):
                raise PermissionError("Permission denied")
            return original_rmtree(path, *args, **kwargs)

        with patch("shutil.rmtree", side_effect=mock_rmtree):
            required = set()
            result = cleanup_orphan_skills(tmp_path, required)

            # Should record error but continue
            assert result["removed_count"] == 0
            assert len(result["errors"]) > 0
            assert any("locked-skill" in err for err in result["errors"])

    def test_cleanup_empty_required_set(self, tmp_path):
        """Test cleanup with empty required set removes all tracked skills."""
        # Setup multiple skills
        (tmp_path / "skill-a").mkdir()
        (tmp_path / "skill-b").mkdir()
        (tmp_path / "skill-c").mkdir()
        track_deployed_skill(tmp_path, "skill-a", "collection")
        track_deployed_skill(tmp_path, "skill-b", "collection")
        track_deployed_skill(tmp_path, "skill-c", "collection")

        # Cleanup with empty required set
        required = set()
        result = cleanup_orphan_skills(tmp_path, required)

        # All skills should be removed
        assert result["removed_count"] == 3
        assert set(result["removed_skills"]) == {"skill-a", "skill-b", "skill-c"}
        assert result["kept_count"] == 0

        # Verify all directories removed
        assert not (tmp_path / "skill-a").exists()
        assert not (tmp_path / "skill-b").exists()
        assert not (tmp_path / "skill-c").exists()

        # Verify index is empty
        index = load_deployment_index(tmp_path)
        assert len(index["deployed_skills"]) == 0


class TestIntegrationScenarios:
    """Test realistic deployment tracking scenarios."""

    def test_full_deployment_lifecycle(self, tmp_path):
        """Test complete deployment lifecycle: deploy -> update -> cleanup."""
        # Phase 1: Initial deployment
        (tmp_path / "skill-a").mkdir()
        (tmp_path / "skill-b").mkdir()
        track_deployed_skill(tmp_path, "skill-a", "claude-mpm")
        track_deployed_skill(tmp_path, "skill-b", "claude-mpm")

        index = load_deployment_index(tmp_path)
        assert len(index["deployed_skills"]) == 2

        # Phase 2: Add new skill
        (tmp_path / "skill-c").mkdir()
        track_deployed_skill(tmp_path, "skill-c", "claude-mpm")

        index = load_deployment_index(tmp_path)
        assert len(index["deployed_skills"]) == 3

        # Phase 3: Agent no longer needs skill-b
        required = {"skill-a", "skill-c"}
        result = cleanup_orphan_skills(tmp_path, required)

        assert result["removed_count"] == 1
        assert "skill-b" in result["removed_skills"]

        # Phase 4: Verify final state
        index = load_deployment_index(tmp_path)
        assert len(index["deployed_skills"]) == 2
        assert "skill-a" in index["deployed_skills"]
        assert "skill-c" in index["deployed_skills"]
        assert "skill-b" not in index["deployed_skills"]

    def test_multi_collection_scenario(self, tmp_path):
        """Test tracking skills from multiple collections."""
        # Deploy skills from different collections
        (tmp_path / "skill-a").mkdir()
        (tmp_path / "skill-b").mkdir()
        (tmp_path / "skill-c").mkdir()

        track_deployed_skill(tmp_path, "skill-a", "claude-mpm")
        track_deployed_skill(tmp_path, "skill-b", "obra-superpowers")
        track_deployed_skill(tmp_path, "skill-c", "claude-mpm")

        # Verify tracking preserves collection info
        index = load_deployment_index(tmp_path)
        assert index["deployed_skills"]["skill-a"]["collection"] == "claude-mpm"
        assert index["deployed_skills"]["skill-b"]["collection"] == "obra-superpowers"
        assert index["deployed_skills"]["skill-c"]["collection"] == "claude-mpm"

        # Cleanup should work regardless of collection
        required = {"skill-a", "skill-c"}
        result = cleanup_orphan_skills(tmp_path, required)

        assert result["removed_count"] == 1
        assert "skill-b" in result["removed_skills"]
