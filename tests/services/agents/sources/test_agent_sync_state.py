"""Unit tests for AgentSyncState service.

Tests cover:
- Database initialization and schema creation
- Source management (CRUD operations)
- File tracking with SHA-256 hashes
- Sync history recording and retrieval
- Error handling and edge cases
- Foreign key constraints and cascades

Target Coverage: 85%+
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from claude_mpm.services.agents.sources.agent_sync_state import (
    AgentSyncState,
    AgentSyncStateError,
    DatabaseError,
)


@pytest.fixture
def temp_db(tmp_path):
    """Temporary database for testing.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        Path to temporary database file
    """
    db_path = tmp_path / "test_sync.db"
    yield db_path
    # Cleanup handled by tmp_path


@pytest.fixture
def sync_state(temp_db):
    """AgentSyncState instance with temporary database.

    Args:
        temp_db: Temporary database path from fixture

    Returns:
        Initialized AgentSyncState instance
    """
    return AgentSyncState(db_path=temp_db)


class TestAgentSyncStateInitialization:
    """Test database initialization and schema creation."""

    def test_creates_database_file(self, temp_db):
        """Test database file creation."""
        assert not temp_db.exists()

        sync_state = AgentSyncState(db_path=temp_db)

        assert temp_db.exists()

    def test_creates_all_tables(self, sync_state, temp_db):
        """Test all required tables created."""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "sources" in tables
        assert "agent_files" in tables
        assert "sync_history" in tables
        assert "schema_metadata" in tables

    def test_creates_indexes(self, sync_state, temp_db):
        """Test performance indexes created."""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "idx_agent_files_source" in indexes
        assert "idx_agent_files_path" in indexes
        assert "idx_sync_history_source_time" in indexes
        assert "idx_sync_history_status" in indexes

    def test_sets_schema_version(self, sync_state, temp_db):
        """Test schema version metadata."""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.execute("SELECT value FROM schema_metadata WHERE key='version'")
        version = cursor.fetchone()[0]
        conn.close()

        assert version == "1"

    def test_enables_foreign_keys(self, sync_state):
        """Test foreign key constraints enabled via cascade behavior."""
        # Register source and track file
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file("test-source", "test.md", "sha123")

        # Delete source should cascade to agent_files
        with sync_state._get_connection() as conn:
            conn.execute("DELETE FROM sources WHERE id='test-source'")

        # Verify file record deleted
        assert sync_state.get_file_hash("test-source", "test.md") is None


class TestSourceManagement:
    """Test source CRUD operations."""

    def test_register_new_source(self, sync_state):
        """Test registering new source."""
        sync_state.register_source(
            source_id="test-source", url="https://github.com/test/repo", enabled=True
        )

        source = sync_state.get_source_info("test-source")
        assert source is not None
        assert source["url"] == "https://github.com/test/repo"
        assert source["enabled"] == 1

    def test_register_source_idempotent(self, sync_state):
        """Test re-registering source updates it."""
        sync_state.register_source("test-source", "https://old.url")
        sync_state.register_source("test-source", "https://new.url")

        source = sync_state.get_source_info("test-source")
        assert source["url"] == "https://new.url"

    def test_update_source_metadata(self, sync_state):
        """Test updating source sync metadata."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.update_source_sync_metadata(
            source_id="test-source", last_sha="abc123", etag='"xyz789"'
        )

        source = sync_state.get_source_info("test-source")
        assert source["last_sha"] == "abc123"
        assert source["etag"] == '"xyz789"'
        assert source["last_sync_time"] is not None

    def test_get_all_sources(self, sync_state):
        """Test retrieving all sources."""
        sync_state.register_source("source1", "https://example.com/1", enabled=True)
        sync_state.register_source("source2", "https://example.com/2", enabled=False)

        all_sources = sync_state.get_all_sources()
        assert len(all_sources) == 2

        enabled_only = sync_state.get_all_sources(enabled_only=True)
        assert len(enabled_only) == 1
        assert enabled_only[0]["id"] == "source1"

    def test_get_nonexistent_source(self, sync_state):
        """Test querying nonexistent source."""
        source = sync_state.get_source_info("nonexistent")
        assert source is None


class TestFileTracking:
    """Test agent file tracking with content hashes."""

    def test_track_new_file(self, sync_state):
        """Test tracking new agent file."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file(
            source_id="test-source",
            file_path="research.md",
            content_sha="abc123def456",
            local_path="/tmp/research.md",
            file_size=1024,
        )

        stored_sha = sync_state.get_file_hash("test-source", "research.md")
        assert stored_sha == "abc123def456"

    def test_track_file_updates_existing(self, sync_state):
        """Test updating tracked file."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file("test-source", "test.md", "old-sha")
        sync_state.track_file("test-source", "test.md", "new-sha")

        stored_sha = sync_state.get_file_hash("test-source", "test.md")
        assert stored_sha == "new-sha"

    def test_has_file_changed_new_file(self, sync_state):
        """Test change detection for new file."""
        sync_state.register_source("test-source", "https://example.com")

        changed = sync_state.has_file_changed("test-source", "new.md", "any-sha")
        assert changed is True

    def test_has_file_changed_unchanged(self, sync_state):
        """Test change detection for unchanged file."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file("test-source", "test.md", "same-sha")

        changed = sync_state.has_file_changed("test-source", "test.md", "same-sha")
        assert changed is False

    def test_has_file_changed_modified(self, sync_state):
        """Test change detection for modified file."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file("test-source", "test.md", "old-sha")

        changed = sync_state.has_file_changed("test-source", "test.md", "new-sha")
        assert changed is True

    def test_get_nonexistent_file_hash(self, sync_state):
        """Test querying nonexistent file."""
        sync_state.register_source("test-source", "https://example.com")

        sha = sync_state.get_file_hash("test-source", "nonexistent.md")
        assert sha is None

    def test_track_file_without_source(self, sync_state):
        """Test tracking file for unregistered source fails."""
        with pytest.raises(sqlite3.IntegrityError):
            with sync_state._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO agent_files (source_id, file_path, content_sha, synced_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        "nonexistent-source",
                        "test.md",
                        "sha",
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )


class TestSyncHistory:
    """Test sync history recording and retrieval."""

    def test_record_successful_sync(self, sync_state):
        """Test recording successful sync."""
        sync_state.register_source("test-source", "https://example.com")

        record_id = sync_state.record_sync_result(
            source_id="test-source",
            status="success",
            files_synced=5,
            files_cached=3,
            files_failed=0,
            duration_ms=1500,
        )

        assert record_id > 0

        history = sync_state.get_sync_history("test-source", limit=1)
        assert len(history) == 1
        assert history[0]["status"] == "success"
        assert history[0]["files_synced"] == 5
        assert history[0]["duration_ms"] == 1500

    def test_record_failed_sync(self, sync_state):
        """Test recording failed sync."""
        sync_state.register_source("test-source", "https://example.com")

        sync_state.record_sync_result(
            source_id="test-source",
            status="error",
            files_synced=0,
            files_failed=10,
            error_message="Network timeout",
        )

        history = sync_state.get_sync_history("test-source")
        assert history[0]["error_message"] == "Network timeout"

    def test_get_sync_history_ordering(self, sync_state):
        """Test sync history returned in descending order."""
        sync_state.register_source("test-source", "https://example.com")

        # Record multiple syncs
        for i in range(5):
            sync_state.record_sync_result(
                source_id="test-source", status="success", files_synced=i
            )

        history = sync_state.get_sync_history("test-source", limit=5)

        # Most recent first (files_synced=4 is latest)
        assert history[0]["files_synced"] == 4
        assert history[4]["files_synced"] == 0

    def test_cleanup_old_history(self, sync_state):
        """Test cleaning up old sync history."""
        sync_state.register_source("test-source", "https://example.com")

        # Insert old record directly (mocking timestamp)
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with sync_state._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sync_history (source_id, sync_time, status)
                VALUES (?, ?, ?)
                """,
                ("test-source", old_time, "success"),
            )

        # Insert recent record
        sync_state.record_sync_result("test-source", "success")

        # Cleanup records older than 30 days
        deleted = sync_state.cleanup_old_history(days=30)

        assert deleted == 1

        # Recent record should remain
        history = sync_state.get_sync_history("test-source")
        assert len(history) == 1


class TestForeignKeyConstraints:
    """Test foreign key constraint behavior."""

    def test_foreign_key_cascade_delete(self, sync_state):
        """Test CASCADE delete removes dependent records."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file("test-source", "test.md", "sha123")
        sync_state.record_sync_result("test-source", "success")

        # Delete source
        with sync_state._get_connection() as conn:
            conn.execute("DELETE FROM sources WHERE id='test-source'")

        # Verify cascaded deletions
        assert sync_state.get_file_hash("test-source", "test.md") is None
        assert len(sync_state.get_sync_history("test-source")) == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_database_queries(self, sync_state):
        """Test querying empty database."""
        assert sync_state.get_all_sources() == []
        assert sync_state.get_source_info("anything") is None
        assert sync_state.get_file_hash("source", "file.md") is None
        assert sync_state.get_sync_history("source") == []

    def test_special_characters_in_paths(self, sync_state):
        """Test handling special characters in file paths."""
        sync_state.register_source("test", "https://example.com")

        special_path = "agent's/file (v2).md"
        sync_state.track_file("test", special_path, "sha123")

        sha = sync_state.get_file_hash("test", special_path)
        assert sha == "sha123"

    def test_very_long_strings(self, sync_state):
        """Test handling very long strings."""
        long_sha = "a" * 1000
        long_path = "path/" * 100 + "file.md"

        sync_state.register_source("test", "https://example.com")
        sync_state.track_file("test", long_path, long_sha)

        stored_sha = sync_state.get_file_hash("test", long_path)
        assert stored_sha == long_sha

    def test_unicode_content(self, sync_state):
        """Test handling Unicode characters."""
        sync_state.register_source("test", "https://example.com")

        unicode_path = "文件.md"
        sync_state.track_file("test", unicode_path, "sha123")

        sha = sync_state.get_file_hash("test", unicode_path)
        assert sha == "sha123"


class TestConnectionManagement:
    """Test database connection lifecycle."""

    def test_connection_cleanup_on_error(self, sync_state):
        """Test connections cleaned up properly on errors."""
        sync_state.register_source("test", "https://example.com")

        # Force an error
        try:
            with sync_state._get_connection() as conn:
                conn.execute("INVALID SQL")
        except sqlite3.OperationalError:
            pass

        # Verify database still works after error
        sync_state.track_file("test", "file.md", "sha")
        assert sync_state.get_file_hash("test", "file.md") == "sha"

    def test_transaction_rollback(self, sync_state):
        """Test transaction rollback on error."""
        sync_state.register_source("test", "https://example.com")

        try:
            with sync_state._get_connection() as conn:
                # This should succeed
                conn.execute(
                    "INSERT INTO agent_files (source_id, file_path, content_sha, synced_at) VALUES (?, ?, ?, ?)",
                    ("test", "file.md", "sha1", datetime.now(timezone.utc).isoformat()),
                )
                # This should fail (duplicate key)
                conn.execute(
                    "INSERT INTO agent_files (source_id, file_path, content_sha, synced_at) VALUES (?, ?, ?, ?)",
                    ("test", "file.md", "sha2", datetime.now(timezone.utc).isoformat()),
                )
        except sqlite3.IntegrityError:
            pass

        # Verify nothing was committed
        assert sync_state.get_file_hash("test", "file.md") is None
