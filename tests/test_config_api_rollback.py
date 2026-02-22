"""Tests for backup and rollback integration scenarios.

Tests cover:
- Deploy creates backup before modifying files
- Failed deploy triggers journal failure recording
- Operation journal records all operations
- Incomplete journal entries detected (simulated crash)
- Backup pruning after multiple operations
- Mode switch rollback scenarios
"""

import json
import time

import pytest

from claude_mpm.services.config_api.backup_manager import BackupManager
from claude_mpm.services.config_api.operation_journal import OperationJournal


@pytest.fixture
def rollback_env(tmp_path):
    """Create a full rollback test environment."""
    backup_root = tmp_path / "backups"
    agents_dir = tmp_path / "project" / ".claude" / "agents"
    skills_dir = tmp_path / "home" / ".claude" / "skills"
    config_dir = tmp_path / "home" / ".claude-mpm" / "config"
    journal_path = tmp_path / "journal" / ".operation-journal.json"

    agents_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)

    # Populate with sample data
    (agents_dir / "engineer.md").write_text("---\nname: engineer\n---\nContent")
    (skills_dir / "tdd").mkdir()
    (skills_dir / "tdd" / "skill.md").write_text("TDD skill")
    (config_dir / "settings.yaml").write_text("mode: selective\n")

    mgr = BackupManager(
        backup_root=backup_root,
        agents_dir=agents_dir,
        skills_dir=skills_dir,
        config_dir=config_dir,
    )
    journal = OperationJournal(journal_path=journal_path)

    return {
        "mgr": mgr,
        "journal": journal,
        "backup_root": backup_root,
        "agents_dir": agents_dir,
        "skills_dir": skills_dir,
        "config_dir": config_dir,
        "journal_path": journal_path,
    }


class TestBackupIntegration:
    def test_deploy_creates_backup(self, rollback_env):
        """Every deploy creates backup before modifying files."""
        mgr = rollback_env["mgr"]
        journal = rollback_env["journal"]

        # Simulate deploy: backup first
        backup = mgr.create_backup("deploy_agent", "agent", "new-agent")

        assert backup.backup_path.exists()
        assert (backup.backup_path / "metadata.json").exists()
        assert backup.files_backed_up > 0

        # Then journal
        op_id = journal.begin_operation(
            "deploy_agent", "agent", "new-agent", backup.backup_id
        )

        # Simulate deploy success
        new_agent = rollback_env["agents_dir"] / "new-agent.md"
        new_agent.write_text("---\nname: new-agent\n---\nNew agent")

        journal.complete_operation(op_id)

        # Verify backup and journal are consistent
        incomplete = journal.check_incomplete_operations()
        assert len(incomplete) == 0

    def test_failed_deploy_triggers_rollback(self, rollback_env):
        """On deploy failure, original state can be restored from backup."""
        mgr = rollback_env["mgr"]
        journal = rollback_env["journal"]
        agents_dir = rollback_env["agents_dir"]

        # Verify original state
        assert (agents_dir / "engineer.md").exists()
        original_content = (agents_dir / "engineer.md").read_text()

        # Backup
        backup = mgr.create_backup("deploy_agent", "agent", "bad-agent")
        op_id = journal.begin_operation(
            "deploy_agent", "agent", "bad-agent", backup.backup_id
        )

        # Simulate destructive failure: accidentally corrupt existing file
        (agents_dir / "engineer.md").write_text("CORRUPTED DATA")

        # Mark as failed
        journal.fail_operation(op_id, "Deployment failed mid-write")

        # Rollback by restoring from backup
        restore = mgr.restore_from_backup(backup.backup_id)
        journal.mark_rolled_back(op_id)

        # Verify original state restored
        assert restore.success is True
        assert (agents_dir / "engineer.md").read_text() == original_content

        # Verify journal reflects rollback
        incomplete = journal.check_incomplete_operations()
        assert len(incomplete) == 0

    def test_journal_records_operations(self, rollback_env):
        """Every deploy writes to operation journal."""
        journal = rollback_env["journal"]

        op1 = journal.begin_operation("deploy_agent", "agent", "a", "b1")
        op2 = journal.begin_operation("undeploy_agent", "agent", "b", "b2")
        op3 = journal.begin_operation("mode_switch", "config", "sel", "b3")

        journal.complete_operation(op1)
        journal.fail_operation(op2, "error")
        journal.complete_operation(op3)

        data = json.loads(rollback_env["journal_path"].read_text())
        assert len(data["entries"]) == 3

        statuses = {e["operation"]: e["status"] for e in data["entries"]}
        assert statuses["deploy_agent"] == "completed"
        assert statuses["undeploy_agent"] == "failed"
        assert statuses["mode_switch"] == "completed"

    def test_incomplete_journal_detected(self, rollback_env):
        """Simulated crash leaves in_progress entry, detected on check."""
        journal = rollback_env["journal"]

        # Begin but never complete (simulates crash)
        op_id = journal.begin_operation("deploy_agent", "agent", "crash-agent", "b1")

        # On restart, check for incomplete
        incomplete = journal.check_incomplete_operations()
        assert len(incomplete) == 1
        assert incomplete[0].id == op_id
        assert incomplete[0].status == "in_progress"
        assert incomplete[0].operation == "deploy_agent"
        assert incomplete[0].entity_id == "crash-agent"

    def test_backup_pruning(self, rollback_env):
        """After 7 backups, pruning leaves only 5."""
        mgr = rollback_env["mgr"]
        backup_root = rollback_env["backup_root"]
        backup_root.mkdir(parents=True, exist_ok=True)

        # Create synthetic backups with distinct timestamps to avoid collisions
        for i in range(7):
            bid = f"2026-02-13T{10 + i:02d}-00-00"
            backup_dir = backup_root / bid
            backup_dir.mkdir(parents=True)
            metadata = {
                "backup_id": bid,
                "created_at": f"2026-02-13T{10 + i:02d}:00:00+00:00",
                "operation": f"op_{i}",
                "entity_type": "agent",
                "entity_id": f"agent_{i}",
                "files_backed_up": 0,
                "size_bytes": 0,
            }
            (backup_dir / "metadata.json").write_text(json.dumps(metadata))

        assert len(mgr.list_backups()) == 7

        # Now set normal limit and prune
        mgr.MAX_BACKUPS = 5
        removed = mgr.prune_old_backups()

        assert removed == 2
        assert len(mgr.list_backups()) == 5


class TestModeSwitchRollback:
    def test_mode_switch_rollback(self, rollback_env):
        """Config write failure during mode switch can be restored."""
        import yaml

        mgr = rollback_env["mgr"]
        journal = rollback_env["journal"]
        config_dir = rollback_env["config_dir"]
        config_path = config_dir / "configuration.yaml"

        # Write initial config
        config_path.write_text(
            yaml.dump(
                {
                    "skills": {"deployment_mode": "full"},
                }
            )
        )

        # Backup before mode switch
        backup = mgr.create_backup("mode_switch", "config", "selective")
        op_id = journal.begin_operation(
            "mode_switch", "config", "selective", backup.backup_id
        )

        # Simulate failed write: corrupt the config
        config_path.write_text("CORRUPTED YAML {{{ broken")

        # Mark as failed
        journal.fail_operation(op_id, "Config write corrupted")

        # Restore config from backup
        restore = mgr.restore_from_backup(backup.backup_id)
        journal.mark_rolled_back(op_id)

        assert restore.success is True

        # Verify config is restored
        restored_config = yaml.safe_load(config_path.read_text())
        assert restored_config["skills"]["deployment_mode"] == "full"

    def test_multiple_operations_with_rollback(self, rollback_env):
        """Multiple operations where one fails and gets rolled back."""
        mgr = rollback_env["mgr"]
        journal = rollback_env["journal"]
        mgr.MAX_BACKUPS = 100

        # Op 1: success
        backup1 = mgr.create_backup("deploy_agent", "agent", "a1")
        op1 = journal.begin_operation("deploy_agent", "agent", "a1", backup1.backup_id)
        journal.complete_operation(op1)

        # Op 2: failure -> rollback
        backup2 = mgr.create_backup("deploy_agent", "agent", "a2")
        op2 = journal.begin_operation("deploy_agent", "agent", "a2", backup2.backup_id)
        journal.fail_operation(op2, "Something went wrong")
        mgr.restore_from_backup(backup2.backup_id)
        journal.mark_rolled_back(op2)

        # Op 3: success
        backup3 = mgr.create_backup("deploy_skill", "skill", "s1")
        op3 = journal.begin_operation("deploy_skill", "skill", "s1", backup3.backup_id)
        journal.complete_operation(op3)

        # Verify final state
        incomplete = journal.check_incomplete_operations()
        assert len(incomplete) == 0

        data = json.loads(rollback_env["journal_path"].read_text())
        statuses = [e["status"] for e in data["entries"]]
        assert statuses == ["completed", "rolled_back", "completed"]
