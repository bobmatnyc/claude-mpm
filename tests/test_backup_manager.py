"""Tests for BackupManager - pre-deployment backup and restore safety.

Tests cover:
- Backup creation with metadata
- Restore from backup
- Listing and sorting backups
- Pruning old backups (keeps MAX_BACKUPS=5)
- Edge cases: empty dirs, nonexistent backups
"""

import json
import time

import pytest

from claude_mpm.services.config_api.backup_manager import (
    BackupManager,
    BackupMetadata,
    BackupResult,
    RestoreResult,
)


@pytest.fixture
def backup_env(tmp_path):
    """Create isolated backup environment with agents/skills/config dirs."""
    backup_root = tmp_path / "backups"
    agents_dir = tmp_path / "project" / ".claude" / "agents"
    skills_dir = tmp_path / "home" / ".claude" / "skills"
    config_dir = tmp_path / "home" / ".claude-mpm" / "config"

    agents_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)

    # Populate with sample files
    (agents_dir / "engineer.md").write_text(
        "---\nname: engineer\ndescription: Core\n---\nBody"
    )
    (agents_dir / "qa.md").write_text("---\nname: qa\ndescription: QA\n---\nBody")
    (skills_dir / "tdd").mkdir()
    (skills_dir / "tdd" / "skill.md").write_text("TDD skill content")
    (config_dir / "settings.yaml").write_text("mode: selective\n")

    mgr = BackupManager(
        backup_root=backup_root,
        agents_dir=agents_dir,
        skills_dir=skills_dir,
        config_dir=config_dir,
    )
    return {
        "mgr": mgr,
        "backup_root": backup_root,
        "agents_dir": agents_dir,
        "skills_dir": skills_dir,
        "config_dir": config_dir,
    }


class TestBackupManagerCreate:
    def test_create_backup_success(self, backup_env):
        """Create backup with agents/skills/config dirs, verify BackupResult."""
        mgr = backup_env["mgr"]
        result = mgr.create_backup("deploy_agent", "agent", "engineer")

        assert isinstance(result, BackupResult)
        assert result.operation == "deploy_agent"
        assert result.entity_type == "agent"
        assert result.entity_id == "engineer"
        assert result.files_backed_up > 0
        assert result.size_bytes > 0
        assert result.backup_path.exists()

    def test_create_backup_creates_metadata_json(self, backup_env):
        """Verify metadata.json contains correct fields."""
        mgr = backup_env["mgr"]
        result = mgr.create_backup("deploy_agent", "agent", "engineer")

        metadata_path = result.backup_path / "metadata.json"
        assert metadata_path.exists()

        metadata = json.loads(metadata_path.read_text())
        assert metadata["operation"] == "deploy_agent"
        assert metadata["entity_type"] == "agent"
        assert metadata["entity_id"] == "engineer"
        assert "created_at" in metadata
        assert "backup_id" in metadata
        assert "files_backed_up" in metadata
        assert "size_bytes" in metadata

    def test_backup_result_has_correct_fields(self, backup_env):
        """BackupResult has all expected fields."""
        mgr = backup_env["mgr"]
        result = mgr.create_backup("undeploy_agent", "agent", "qa")

        assert result.backup_id  # non-empty
        assert result.backup_path.is_dir()
        assert isinstance(result.files_backed_up, int)
        assert isinstance(result.size_bytes, int)
        assert result.created_at  # ISO format string
        assert result.operation == "undeploy_agent"
        assert result.entity_type == "agent"
        assert result.entity_id == "qa"

    def test_backup_copies_agents_dir(self, backup_env):
        """Verify agents directory is copied into backup."""
        mgr = backup_env["mgr"]
        result = mgr.create_backup("deploy_agent", "agent", "test")

        agents_backup = result.backup_path / "agents"
        assert agents_backup.exists()
        assert (agents_backup / "engineer.md").exists()
        assert (agents_backup / "qa.md").exists()

    def test_backup_copies_skills_dir(self, backup_env):
        """Verify skills directory is copied into backup."""
        mgr = backup_env["mgr"]
        result = mgr.create_backup("deploy_skill", "skill", "tdd")

        skills_backup = result.backup_path / "skills"
        assert skills_backup.exists()
        assert (skills_backup / "tdd" / "skill.md").exists()

    def test_backup_copies_config_dir(self, backup_env):
        """Verify config directory is copied into backup."""
        mgr = backup_env["mgr"]
        result = mgr.create_backup("mode_switch", "config", "selective")

        config_backup = result.backup_path / "config"
        assert config_backup.exists()
        assert (config_backup / "settings.yaml").exists()

    def test_backup_empty_directory(self, tmp_path):
        """Backup when agents/skills dirs don't exist - should handle gracefully."""
        backup_root = tmp_path / "backups"
        agents_dir = tmp_path / "nonexistent_agents"
        skills_dir = tmp_path / "nonexistent_skills"
        config_dir = tmp_path / "nonexistent_config"

        mgr = BackupManager(
            backup_root=backup_root,
            agents_dir=agents_dir,
            skills_dir=skills_dir,
            config_dir=config_dir,
        )

        result = mgr.create_backup("deploy_agent", "agent", "test")

        assert isinstance(result, BackupResult)
        assert result.files_backed_up == 0
        assert result.size_bytes == 0
        assert result.backup_path.exists()

        # metadata.json should still be created
        assert (result.backup_path / "metadata.json").exists()


class TestBackupManagerRestore:
    def test_restore_from_backup(self, backup_env):
        """Create backup, modify original, restore, verify originals restored."""
        mgr = backup_env["mgr"]
        agents_dir = backup_env["agents_dir"]

        # Create backup
        result = mgr.create_backup("undeploy_agent", "agent", "engineer")

        # Modify original - remove an agent
        (agents_dir / "engineer.md").unlink()
        assert not (agents_dir / "engineer.md").exists()

        # Restore
        restore = mgr.restore_from_backup(result.backup_id)

        assert isinstance(restore, RestoreResult)
        assert restore.success is True
        assert restore.files_restored > 0
        assert restore.errors == []

        # Verify file is back
        assert (agents_dir / "engineer.md").exists()

    def test_restore_nonexistent_backup(self, backup_env):
        """Attempting restore from nonexistent backup ID should fail gracefully."""
        mgr = backup_env["mgr"]

        restore = mgr.restore_from_backup("nonexistent-backup-id")

        assert isinstance(restore, RestoreResult)
        assert restore.success is False
        assert restore.files_restored == 0
        assert len(restore.errors) > 0
        assert "not found" in restore.errors[0].lower()


def _create_synthetic_backup(
    backup_root, backup_id, created_at_iso, operation, entity_id
):
    """Create a backup directory directly with a specific timestamp for testing."""
    backup_dir = backup_root / backup_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "backup_id": backup_id,
        "created_at": created_at_iso,
        "operation": operation,
        "entity_type": "agent",
        "entity_id": entity_id,
        "files_backed_up": 0,
        "size_bytes": 0,
    }
    (backup_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    return backup_id


class TestBackupManagerList:
    def test_list_backups_sorted_by_date(self, backup_env):
        """Create multiple backups with distinct timestamps, verify newest first."""
        mgr = backup_env["mgr"]
        backup_root = backup_env["backup_root"]
        backup_root.mkdir(parents=True, exist_ok=True)

        # Create backups with explicit distinct timestamps
        ids = []
        ids.append(
            _create_synthetic_backup(
                backup_root,
                "2026-02-13T10-00-00",
                "2026-02-13T10:00:00+00:00",
                "op_0",
                "agent_0",
            )
        )
        ids.append(
            _create_synthetic_backup(
                backup_root,
                "2026-02-13T11-00-00",
                "2026-02-13T11:00:00+00:00",
                "op_1",
                "agent_1",
            )
        )
        ids.append(
            _create_synthetic_backup(
                backup_root,
                "2026-02-13T12-00-00",
                "2026-02-13T12:00:00+00:00",
                "op_2",
                "agent_2",
            )
        )

        backups = mgr.list_backups()

        assert len(backups) == 3
        assert all(isinstance(b, BackupMetadata) for b in backups)
        # Verify descending order by created_at (newest first)
        assert backups[0].backup_id == "2026-02-13T12-00-00"
        assert backups[1].backup_id == "2026-02-13T11-00-00"
        assert backups[2].backup_id == "2026-02-13T10-00-00"

    def test_list_backups_empty(self, tmp_path):
        """List backups when no backups exist."""
        mgr = BackupManager(backup_root=tmp_path / "empty_backups")
        backups = mgr.list_backups()
        assert backups == []


class TestBackupManagerPrune:
    def test_prune_old_backups_keeps_max_5(self, backup_env):
        """Create 7 backups, prune, verify only 5 remain (newest 5)."""
        mgr = backup_env["mgr"]
        backup_root = backup_env["backup_root"]
        backup_root.mkdir(parents=True, exist_ok=True)

        for i in range(7):
            _create_synthetic_backup(
                backup_root,
                f"2026-02-13T{10 + i:02d}-00-00",
                f"2026-02-13T{10 + i:02d}:00:00+00:00",
                f"op_{i}",
                f"agent_{i}",
            )

        assert len(mgr.list_backups()) == 7

        mgr.MAX_BACKUPS = 5
        removed = mgr.prune_old_backups()

        assert removed == 2
        remaining = mgr.list_backups()
        assert len(remaining) == 5

    def test_prune_removes_oldest_first(self, backup_env):
        """Verify oldest backups are pruned, newest are kept."""
        mgr = backup_env["mgr"]
        backup_root = backup_env["backup_root"]
        backup_root.mkdir(parents=True, exist_ok=True)

        all_ids = []
        for i in range(7):
            bid = f"2026-02-13T{10 + i:02d}-00-00"
            _create_synthetic_backup(
                backup_root,
                bid,
                f"2026-02-13T{10 + i:02d}:00:00+00:00",
                f"op_{i}",
                f"agent_{i}",
            )
            all_ids.append(bid)

        mgr.MAX_BACKUPS = 5
        mgr.prune_old_backups()

        remaining = mgr.list_backups()
        remaining_ids = {b.backup_id for b in remaining}

        # The oldest 2 (hours 10 and 11) should be pruned
        assert all_ids[0] not in remaining_ids
        assert all_ids[1] not in remaining_ids
        # The newest 5 (hours 12-16) should remain
        for kept_id in all_ids[2:]:
            assert kept_id in remaining_ids

    def test_prune_noop_when_under_limit(self, backup_env):
        """No backups removed when count <= MAX_BACKUPS."""
        mgr = backup_env["mgr"]
        backup_root = backup_env["backup_root"]
        backup_root.mkdir(parents=True, exist_ok=True)

        for i in range(3):
            _create_synthetic_backup(
                backup_root,
                f"2026-02-13T{10 + i:02d}-00-00",
                f"2026-02-13T{10 + i:02d}:00:00+00:00",
                f"op_{i}",
                f"agent_{i}",
            )

        mgr.MAX_BACKUPS = 5
        removed = mgr.prune_old_backups()
        assert removed == 0
