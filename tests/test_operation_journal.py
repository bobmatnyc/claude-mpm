"""Tests for OperationJournal - crash-recovery write-ahead log.

Tests cover:
- Begin, complete, fail operation lifecycle
- Checking for incomplete (in_progress) operations
- Marking operations as rolled back
- Journal file auto-creation
- Multiple concurrent operations
"""

import json

import pytest

from claude_mpm.services.config_api.operation_journal import (
    JournalEntry,
    OperationJournal,
)


@pytest.fixture
def journal(tmp_path):
    """Create OperationJournal writing to tmp_path."""
    journal_path = tmp_path / ".operation-journal.json"
    return OperationJournal(journal_path=journal_path)


@pytest.fixture
def journal_path(tmp_path):
    """Return the journal file path for direct inspection."""
    return tmp_path / ".operation-journal.json"


class TestBeginOperation:
    def test_begin_operation_creates_entry(self, journal, journal_path):
        """Begin operation creates journal file with entry, status=in_progress."""
        op_id = journal.begin_operation(
            "deploy_agent", "agent", "engineer", "backup-001"
        )

        assert op_id.startswith("op-")
        assert journal_path.exists()

        data = json.loads(journal_path.read_text())
        assert data["version"] == "1.0"
        assert len(data["entries"]) == 1

        entry = data["entries"][0]
        assert entry["id"] == op_id
        assert entry["operation"] == "deploy_agent"
        assert entry["entity_type"] == "agent"
        assert entry["entity_id"] == "engineer"
        assert entry["backup_id"] == "backup-001"
        assert entry["status"] == "in_progress"
        assert entry["started_at"]  # Non-empty ISO string
        assert entry["completed_at"] is None

    def test_begin_operation_with_rollback_info(self, journal, journal_path):
        """Begin operation accepts optional rollback_info."""
        rollback = {"previous_mode": "full"}
        op_id = journal.begin_operation(
            "mode_switch",
            "config",
            "selective",
            "backup-002",
            rollback_info=rollback,
        )

        data = json.loads(journal_path.read_text())
        entry = data["entries"][0]
        assert entry["rollback_info"] == {"previous_mode": "full"}


class TestCompleteOperation:
    def test_complete_operation_updates_status(self, journal, journal_path):
        """Complete operation sets status=completed and completed_at timestamp."""
        op_id = journal.begin_operation("deploy_agent", "agent", "qa", "backup-003")
        journal.complete_operation(op_id)

        data = json.loads(journal_path.read_text())
        entry = data["entries"][0]
        assert entry["status"] == "completed"
        assert entry["completed_at"] is not None  # ISO timestamp
        assert entry["error"] is None

    def test_complete_nonexistent_raises(self, journal):
        """Completing an unknown operation ID raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            journal.complete_operation("op-nonexistent")


class TestFailOperation:
    def test_fail_operation_records_error(self, journal, journal_path):
        """Fail operation sets status=failed, records error message."""
        op_id = journal.begin_operation("deploy_skill", "skill", "tdd", "backup-004")
        journal.fail_operation(op_id, "Skill directory not found")

        data = json.loads(journal_path.read_text())
        entry = data["entries"][0]
        assert entry["status"] == "failed"
        assert entry["error"] == "Skill directory not found"
        assert entry["completed_at"] is not None


class TestCheckIncomplete:
    def test_check_incomplete_finds_in_progress(self, journal):
        """check_incomplete_operations returns entries with status=in_progress."""
        op1 = journal.begin_operation("op1", "agent", "a", "b1")
        op2 = journal.begin_operation("op2", "agent", "b", "b2")

        incomplete = journal.check_incomplete_operations()
        assert len(incomplete) == 2
        assert all(isinstance(e, JournalEntry) for e in incomplete)
        assert all(e.status == "in_progress" for e in incomplete)

    def test_check_incomplete_ignores_completed(self, journal):
        """Completed operations are not returned by check_incomplete."""
        op1 = journal.begin_operation("op1", "agent", "a", "b1")
        op2 = journal.begin_operation("op2", "agent", "b", "b2")
        journal.complete_operation(op1)

        incomplete = journal.check_incomplete_operations()
        assert len(incomplete) == 1
        assert incomplete[0].id == op2

    def test_check_incomplete_ignores_failed(self, journal):
        """Failed operations are not returned by check_incomplete."""
        op1 = journal.begin_operation("op1", "agent", "a", "b1")
        journal.fail_operation(op1, "error")

        incomplete = journal.check_incomplete_operations()
        assert len(incomplete) == 0

    def test_check_incomplete_empty_journal(self, journal):
        """No incomplete operations in a fresh journal."""
        incomplete = journal.check_incomplete_operations()
        assert incomplete == []


class TestMarkRolledBack:
    def test_mark_rolled_back(self, journal, journal_path):
        """Mark rolled_back sets status correctly."""
        op_id = journal.begin_operation(
            "deploy_agent", "agent", "engineer", "backup-005"
        )
        journal.mark_rolled_back(op_id)

        data = json.loads(journal_path.read_text())
        entry = data["entries"][0]
        assert entry["status"] == "rolled_back"
        assert entry["completed_at"] is not None

    def test_rolled_back_not_in_incomplete(self, journal):
        """Rolled-back operations are not returned by check_incomplete."""
        op_id = journal.begin_operation("op1", "agent", "a", "b1")
        journal.mark_rolled_back(op_id)

        incomplete = journal.check_incomplete_operations()
        assert len(incomplete) == 0


class TestJournalFileManagement:
    def test_journal_file_creation_if_not_exists(self, tmp_path):
        """Journal creates file if it doesn't exist on first operation."""
        journal_path = tmp_path / "subdir" / "journal.json"
        assert not journal_path.exists()

        journal = OperationJournal(journal_path=journal_path)
        journal.begin_operation("op", "agent", "a", "b1")

        assert journal_path.exists()
        data = json.loads(journal_path.read_text())
        assert data["version"] == "1.0"

    def test_corrupt_journal_resets(self, tmp_path):
        """Corrupt journal file is handled gracefully (reset to empty)."""
        journal_path = tmp_path / "journal.json"
        journal_path.write_text("not valid json {{{{")

        journal = OperationJournal(journal_path=journal_path)
        op_id = journal.begin_operation("op", "agent", "a", "b1")

        # Should succeed despite corrupt file
        assert op_id.startswith("op-")
        data = json.loads(journal_path.read_text())
        assert len(data["entries"]) == 1


class TestConcurrentOperations:
    def test_multiple_concurrent_operations(self, journal, journal_path):
        """Multiple begin_operation calls create separate entries."""
        op1 = journal.begin_operation("deploy", "agent", "a", "b1")
        op2 = journal.begin_operation("deploy", "agent", "b", "b2")
        op3 = journal.begin_operation("undeploy", "skill", "c", "b3")

        data = json.loads(journal_path.read_text())
        assert len(data["entries"]) == 3

        ids = {e["id"] for e in data["entries"]}
        assert op1 in ids
        assert op2 in ids
        assert op3 in ids

    def test_mixed_status_operations(self, journal):
        """Operations in different states coexist correctly."""
        op1 = journal.begin_operation("op1", "agent", "a", "b1")
        op2 = journal.begin_operation("op2", "agent", "b", "b2")
        op3 = journal.begin_operation("op3", "agent", "c", "b3")

        journal.complete_operation(op1)
        journal.fail_operation(op2, "error")
        # op3 stays in_progress

        incomplete = journal.check_incomplete_operations()
        assert len(incomplete) == 1
        assert incomplete[0].id == op3
