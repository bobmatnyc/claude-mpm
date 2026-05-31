"""Tests for scripts/migrate_messaging_to_trusty.py.

Verifies:
1. Core transform: DB row → trusty-memory palace entry
2. Missing DB → graceful exit (returns 0, no crash)
3. Empty table → graceful exit (returns 0, no crash)
4. Full round-trip: rows in temp DB → correct JSONL output
5. Dry-run mode: returns count but writes no output
6. MessageService emits a DeprecationWarning on first instantiation
"""

import json
import sqlite3
import warnings
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_test_db(db_path: Path, rows: list[dict] | None = None) -> None:
    """Create a minimal messaging.db with the schema from MessagingDatabase."""
    conn = sqlite3.connect(str(db_path), timeout=1.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            from_project TEXT NOT NULL,
            from_agent TEXT NOT NULL DEFAULT 'pm',
            to_project TEXT NOT NULL,
            to_agent TEXT NOT NULL DEFAULT 'pm',
            message_type TEXT NOT NULL DEFAULT 'notification',
            priority TEXT NOT NULL DEFAULT 'normal',
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'unread',
            created_at TEXT NOT NULL,
            read_at TEXT,
            replied_to TEXT,
            task_injected INTEGER NOT NULL DEFAULT 0,
            metadata TEXT,
            attachments TEXT
        )
    """)
    if rows:
        for row in rows:
            conn.execute(
                """
                INSERT INTO messages
                    (id, from_project, from_agent, to_project, to_agent,
                     message_type, priority, subject, body, status, created_at,
                     read_at, replied_to, task_injected, metadata, attachments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("id", "msg-001"),
                    row.get("from_project", "/project1"),
                    row.get("from_agent", "pm"),
                    row.get("to_project", "/project2"),
                    row.get("to_agent", "engineer"),
                    row.get("message_type", "task"),
                    row.get("priority", "normal"),
                    row.get("subject", "Test subject"),
                    row.get("body", "Test body"),
                    row.get("status", "unread"),
                    row.get("created_at", "2026-01-01T00:00:00+00:00"),
                    row.get("read_at"),
                    row.get("replied_to"),
                    int(row.get("task_injected", 0)),
                    row.get("metadata", "{}"),
                    row.get("attachments", "[]"),
                ),
            )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

import os
import sys

# Ensure the scripts/ directory is importable without installing
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from migrate_messaging_to_trusty import (
    _read_messages,
    _row_to_palace_entry,
    migrate,
)

# ---------------------------------------------------------------------------
# Unit tests: _row_to_palace_entry
# ---------------------------------------------------------------------------


class TestRowToPalaceEntry:
    """Unit-test the per-row transformation."""

    def test_basic_fields(self):
        row = {
            "id": "msg-20260101-abc12345",
            "from_project": "/home/user/projectA",
            "from_agent": "pm",
            "to_project": "/home/user/projectB",
            "to_agent": "engineer",
            "message_type": "task",
            "priority": "high",
            "subject": "Do the thing",
            "body": "Please do the thing ASAP.",
            "status": "unread",
            "created_at": "2026-01-01T12:00:00+00:00",
            "read_at": None,
            "replied_to": None,
            "task_injected": 0,
            "metadata": "{}",
            "attachments": "[]",
        }
        entry = _row_to_palace_entry(row)

        assert entry["palace"] == "messaging"
        assert entry["type"] == "message"
        assert entry["key"] == "message/msg-20260101-abc12345"

        val = entry["value"]
        assert val["id"] == "msg-20260101-abc12345"
        assert val["from_project"] == "/home/user/projectA"
        assert val["to_project"] == "/home/user/projectB"
        assert val["subject"] == "Do the thing"
        assert val["priority"] == "high"
        assert val["message_type"] == "task"
        assert val["status"] == "unread"
        assert val["task_injected"] is False
        assert val["metadata"] == {}
        assert val["attachments"] == []
        assert val["migrated_from"] == "messaging.db"

    def test_json_metadata_decoded(self):
        row = {
            "id": "msg-meta",
            "from_project": "/p1",
            "from_agent": "pm",
            "to_project": "/p2",
            "to_agent": "pm",
            "message_type": "notification",
            "priority": "normal",
            "subject": "Meta test",
            "body": "body",
            "status": "read",
            "created_at": "2026-01-01T00:00:00+00:00",
            "read_at": "2026-01-02T00:00:00+00:00",
            "replied_to": None,
            "task_injected": 1,
            "metadata": '{"reply_to": "msg-abc"}',
            "attachments": '["/path/to/file.txt"]',
        }
        entry = _row_to_palace_entry(row)
        val = entry["value"]

        assert val["metadata"] == {"reply_to": "msg-abc"}
        assert val["attachments"] == ["/path/to/file.txt"]
        assert val["task_injected"] is True

    def test_malformed_json_falls_back_gracefully(self):
        row = {
            "id": "msg-bad-json",
            "from_project": "/p1",
            "from_agent": "pm",
            "to_project": "/p2",
            "to_agent": "pm",
            "message_type": "notification",
            "priority": "normal",
            "subject": "Bad JSON",
            "body": "body",
            "status": "unread",
            "created_at": "2026-01-01T00:00:00+00:00",
            "read_at": None,
            "replied_to": None,
            "task_injected": 0,
            "metadata": "not-valid-json",
            "attachments": "{also bad}",
        }
        entry = _row_to_palace_entry(row)
        # Should fall back to empty collections, not raise
        assert entry["value"]["metadata"] == {}
        assert entry["value"]["attachments"] == []


# ---------------------------------------------------------------------------
# Integration tests: migrate()
# ---------------------------------------------------------------------------


class TestMigrateFunction:
    """Integration tests for the migrate() function."""

    def test_missing_db_returns_zero(self, tmp_path):
        """Non-existent DB should be handled gracefully."""
        non_existent = tmp_path / "no_such.db"
        count = migrate(db_path=non_existent, output_path=None, dry_run=True)
        assert count == 0

    def test_empty_table_returns_zero(self, tmp_path):
        """DB with empty messages table should return 0."""
        db = tmp_path / "messaging.db"
        _create_test_db(db, rows=[])
        count = migrate(db_path=db, output_path=None, dry_run=True)
        assert count == 0

    def test_dry_run_returns_count_no_output(self, tmp_path, capsys):
        """Dry run should return the count and not write to stdout."""
        db = tmp_path / "messaging.db"
        _create_test_db(
            db,
            rows=[
                {"id": "msg-001", "subject": "Hello"},
                {"id": "msg-002", "subject": "World"},
            ],
        )
        out_file = tmp_path / "output.jsonl"

        count = migrate(db_path=db, output_path=out_file, dry_run=True)

        assert count == 2
        # Dry run: output file must NOT be created
        assert not out_file.exists()
        # Dry run: stdout should be empty (messages go to stderr via logger)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_output_to_file(self, tmp_path):
        """Migrate should write valid JSONL to --output file."""
        db = tmp_path / "messaging.db"
        _create_test_db(
            db,
            rows=[
                {
                    "id": "msg-001",
                    "from_project": "/proj/a",
                    "to_project": "/proj/b",
                    "subject": "First",
                    "body": "Body 1",
                    "message_type": "task",
                    "priority": "high",
                },
                {
                    "id": "msg-002",
                    "from_project": "/proj/a",
                    "to_project": "/proj/b",
                    "subject": "Second",
                    "body": "Body 2",
                    "message_type": "notification",
                    "priority": "normal",
                },
            ],
        )
        out_file = tmp_path / "output.jsonl"

        count = migrate(db_path=db, output_path=out_file, dry_run=False)

        assert count == 2
        assert out_file.exists()

        lines = out_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

        for line in lines:
            entry = json.loads(line)
            assert entry["palace"] == "messaging"
            assert entry["type"] == "message"
            assert entry["key"].startswith("message/msg-")
            assert "subject" in entry["value"]
            assert entry["value"]["migrated_from"] == "messaging.db"

        # Verify ordering preserved
        entries = [json.loads(line) for line in lines]
        assert entries[0]["value"]["subject"] == "First"
        assert entries[1]["value"]["subject"] == "Second"

    def test_output_to_stdout(self, tmp_path, capsys):
        """When output_path is None, JSONL should go to stdout."""
        db = tmp_path / "messaging.db"
        _create_test_db(db, rows=[{"id": "msg-stdout", "subject": "StdoutTest"}])

        count = migrate(db_path=db, output_path=None, dry_run=False)

        assert count == 1
        captured = capsys.readouterr()
        lines = captured.out.strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["value"]["subject"] == "StdoutTest"


# ---------------------------------------------------------------------------
# CLI tests: main()
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main() CLI entry point."""

    def test_main_missing_db_exits_zero(self, tmp_path):
        """Missing DB → main() returns 0 (not an error)."""
        from migrate_messaging_to_trusty import main

        result = main(["--db", str(tmp_path / "nope.db"), "--dry-run"])
        assert result == 0

    def test_main_with_output_file(self, tmp_path):
        """main() with --output should create the file."""
        from migrate_messaging_to_trusty import main

        db = tmp_path / "messaging.db"
        _create_test_db(db, rows=[{"id": "msg-cli", "subject": "CLI test"}])
        out = tmp_path / "out.jsonl"

        result = main(["--db", str(db), "--output", str(out)])
        assert result == 0
        assert out.exists()
        entry = json.loads(out.read_text().strip())
        assert entry["value"]["id"] == "msg-cli"


# ---------------------------------------------------------------------------
# Deprecation warning tests: MessageService
# ---------------------------------------------------------------------------


class TestMessageServiceDeprecation:
    """Verify MessageService emits DeprecationWarning on instantiation."""

    def test_deprecation_warning_emitted(self, tmp_path):
        """Instantiating MessageService should produce a DeprecationWarning."""
        import importlib

        # Reset the module-level flag so the warning fires fresh in this test.
        import claude_mpm.services.communication.message_service as ms_mod

        original = ms_mod._DEPRECATION_WARNED
        ms_mod._DEPRECATION_WARNED = False
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    ms_mod.MessageService(tmp_path)
                except Exception:
                    # May fail due to missing deps in test env; warning still fires
                    pass

            dep_warnings = [
                w for w in caught if issubclass(w.category, DeprecationWarning)
            ]
            assert dep_warnings, (
                "Expected at least one DeprecationWarning from MessageService"
            )
            assert (
                "trusty-memory" in str(dep_warnings[0].message).lower()
                or "deprecated" in str(dep_warnings[0].message).lower()
            )
        finally:
            ms_mod._DEPRECATION_WARNED = original

    def test_deprecation_warning_emitted_only_once(self, tmp_path):
        """MessageService should warn only once per process (module-level guard)."""
        import claude_mpm.services.communication.message_service as ms_mod

        ms_mod._DEPRECATION_WARNED = False
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                for _ in range(3):
                    try:
                        ms_mod.MessageService(tmp_path)
                    except Exception:
                        pass

            dep_warnings = [
                w for w in caught if issubclass(w.category, DeprecationWarning)
            ]
            # Should see exactly one warning despite three instantiations
            assert len(dep_warnings) == 1
        finally:
            ms_mod._DEPRECATION_WARNED = False
