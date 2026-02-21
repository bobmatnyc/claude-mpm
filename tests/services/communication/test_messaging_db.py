"""
Tests for SQLite messaging database.
"""

import json
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from claude_mpm.services.communication.messaging_db import MessagingDatabase


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_messaging.db"
    return MessagingDatabase(db_path)


@pytest.fixture
def sample_message():
    """Create a sample message dictionary."""
    return {
        "id": "msg-20240101-123456-abc123",
        "from_project": "/home/user/project1",
        "from_agent": "pm",
        "to_project": "/home/user/project2",
        "to_agent": "engineer",
        "type": "task",
        "priority": "high",
        "subject": "Test Task",
        "body": "This is a test task message.",
        "status": "unread",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reply_to": None,
        "metadata": {"key": "value"},
        "attachments": ["file1.txt", "file2.py"],
    }


class TestMessagingDatabase:
    """Test MessagingDatabase functionality."""

    def test_table_creation(self, tmp_db):
        """Test that tables are created on initialization."""
        # Tables should be created automatically
        with tmp_db.get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

        assert "sessions" in tables
        assert "messages" in tables

    def test_wal_mode_enabled(self, tmp_db):
        """Test that WAL mode is enabled."""
        with tmp_db.get_connection() as conn:
            cursor = conn.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]

        assert mode == "wal"

    def test_insert_and_get_message(self, tmp_db, sample_message):
        """Test inserting and retrieving a message."""
        # Insert message
        message_id = tmp_db.insert_message(sample_message)
        assert message_id == sample_message["id"]

        # Retrieve message
        retrieved = tmp_db.get_message(message_id)
        assert retrieved is not None
        assert retrieved["id"] == sample_message["id"]
        assert retrieved["subject"] == sample_message["subject"]
        assert retrieved["body"] == sample_message["body"]
        assert retrieved["metadata"] == sample_message["metadata"]
        assert retrieved["attachments"] == sample_message["attachments"]

    def test_list_messages(self, tmp_db):
        """Test listing messages with filters."""
        # Insert multiple messages
        messages = [
            {
                "id": f"msg-{i}",
                "from_project": "/project1",
                "to_project": "/project2",
                "subject": f"Message {i}",
                "body": f"Body {i}",
                "status": "unread" if i < 3 else "read",
                "priority": "high" if i == 0 else "normal",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(5)
        ]

        for msg in messages:
            tmp_db.insert_message(msg)

        # List all messages
        all_messages = tmp_db.list_messages()
        assert len(all_messages) == 5

        # Filter by status
        unread_messages = tmp_db.list_messages(status="unread")
        assert len(unread_messages) == 3

        read_messages = tmp_db.list_messages(status="read")
        assert len(read_messages) == 2

    def test_update_message_status(self, tmp_db, sample_message):
        """Test updating message status."""
        # Insert message
        tmp_db.insert_message(sample_message)

        # Update status to read
        success = tmp_db.update_message_status(sample_message["id"], "read")
        assert success is True

        # Verify status changed
        message = tmp_db.get_message(sample_message["id"])
        assert message["status"] == "read"
        assert message["read_at"] is not None

        # Update non-existent message
        success = tmp_db.update_message_status("non-existent", "read")
        assert success is False

    def test_mark_task_injected(self, tmp_db, sample_message):
        """Test marking a message as task injected."""
        # Insert message
        tmp_db.insert_message(sample_message)

        # Mark as task injected
        success = tmp_db.mark_task_injected(sample_message["id"])
        assert success is True

        # Verify task_injected flag
        message = tmp_db.get_message(sample_message["id"])
        assert message["task_injected"] is True

    def test_get_unread_count(self, tmp_db):
        """Test getting unread message count."""
        # Insert messages with different statuses and agents
        messages = [
            {"id": "msg-1", "status": "unread", "to_agent": "pm"},
            {"id": "msg-2", "status": "unread", "to_agent": "engineer"},
            {"id": "msg-3", "status": "read", "to_agent": "pm"},
            {"id": "msg-4", "status": "unread", "to_agent": "pm"},
        ]

        for msg in messages:
            full_msg = {
                "from_project": "/p1",
                "to_project": "/p2",
                "subject": "Test",
                "body": "Test",
                "created_at": datetime.now(timezone.utc).isoformat(),
                **msg,
            }
            tmp_db.insert_message(full_msg)

        # Total unread count
        assert tmp_db.get_unread_count() == 3

        # Unread count for specific agent
        assert tmp_db.get_unread_count(to_agent="pm") == 2
        assert tmp_db.get_unread_count(to_agent="engineer") == 1

    def test_session_registration(self, tmp_db):
        """Test session registration and management."""
        # Register session
        session_id = "session-123"
        project_path = "/home/user/myproject"
        pid = 12345

        tmp_db.register_session(session_id, project_path, pid)

        # List active sessions
        sessions = tmp_db.list_active_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == session_id
        assert sessions[0]["project_path"] == project_path
        assert sessions[0]["project_name"] == "myproject"
        assert sessions[0]["pid"] == pid
        assert sessions[0]["status"] == "active"

    def test_session_heartbeat(self, tmp_db):
        """Test updating session heartbeat."""
        # Register session
        session_id = "session-456"
        tmp_db.register_session(session_id, "/project", 123)

        # Get initial last_active
        sessions = tmp_db.list_active_sessions()
        initial_time = sessions[0]["last_active"]

        # Update heartbeat (with small delay to ensure different timestamp)
        import time

        time.sleep(0.1)
        tmp_db.update_heartbeat(session_id)

        # Verify last_active updated
        sessions = tmp_db.list_active_sessions()
        assert sessions[0]["last_active"] > initial_time

    def test_session_deregistration(self, tmp_db):
        """Test deregistering a session."""
        # Register session
        session_id = "session-789"
        tmp_db.register_session(session_id, "/project", 123)

        # Deregister session
        tmp_db.deregister_session(session_id)

        # Verify session is inactive
        sessions = tmp_db.list_active_sessions()
        assert len(sessions) == 0

    def test_cleanup_stale_sessions(self, tmp_db):
        """Test cleaning up stale sessions."""
        # Register sessions with different last_active times
        now = datetime.now(timezone.utc)

        # Active session
        tmp_db.register_session("active-session", "/project1", 111)

        # Stale session (manually set old last_active)
        with tmp_db.get_connection() as conn:
            old_time = (now - timedelta(hours=2)).isoformat()
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, project_path, project_name,
                    started_at, last_active, status, pid
                ) VALUES (?, ?, ?, ?, ?, 'active', ?)
                """,
                ("stale-session", "/project2", "project2", old_time, old_time, 222),
            )

        # Clean up sessions older than 60 minutes
        count = tmp_db.cleanup_stale_sessions(timeout_minutes=60)
        assert count == 1

        # Verify only active session remains
        sessions = tmp_db.list_active_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "active-session"

    def test_get_messages_for_agent(self, tmp_db):
        """Test getting messages for a specific agent."""
        # Insert messages for different agents
        messages = [
            {"to_agent": "pm", "status": "unread"},
            {"to_agent": "pm", "status": "read"},
            {"to_agent": "engineer", "status": "unread"},
            {"to_agent": "pm", "status": "unread"},
        ]

        for i, msg_data in enumerate(messages):
            msg = {
                "id": f"msg-{i}",
                "from_project": "/p1",
                "to_project": "/p2",
                "subject": f"Message {i}",
                "body": "Test",
                "created_at": datetime.now(timezone.utc).isoformat(),
                **msg_data,
            }
            tmp_db.insert_message(msg)

        # Get all messages for pm
        pm_messages = tmp_db.get_messages_for_agent("pm")
        assert len(pm_messages) == 3

        # Get unread messages for pm
        pm_unread = tmp_db.get_messages_for_agent("pm", status="unread")
        assert len(pm_unread) == 2

    def test_get_high_priority_messages(self, tmp_db):
        """Test getting high priority messages."""
        # Insert messages with different priorities
        priorities = ["urgent", "high", "normal", "high", "low", "urgent"]
        for i, priority in enumerate(priorities):
            msg = {
                "id": f"msg-{i}",
                "from_project": "/p1",
                "to_project": "/p2",
                "subject": f"Message {i}",
                "body": "Test",
                "priority": priority,
                "status": "unread",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            tmp_db.insert_message(msg)

        # Get high priority messages (urgent and high)
        high_priority = tmp_db.get_high_priority_messages()
        assert len(high_priority) == 4  # 2 urgent + 2 high

        # Verify ordering (urgent first)
        assert high_priority[0]["priority"] == "urgent"
        assert high_priority[1]["priority"] == "urgent"

    def test_concurrent_access(self, tmp_db, sample_message):
        """Test that WAL mode allows concurrent access."""
        import threading
        import time

        # Insert initial message
        tmp_db.insert_message(sample_message)

        results = []

        def read_message():
            """Read message in separate thread."""
            msg = tmp_db.get_message(sample_message["id"])
            results.append(msg is not None)

        def update_message():
            """Update message in separate thread."""
            time.sleep(0.05)  # Small delay to ensure read starts first
            success = tmp_db.update_message_status(sample_message["id"], "read")
            results.append(success)

        # Start concurrent operations
        read_thread = threading.Thread(target=read_message)
        update_thread = threading.Thread(target=update_message)

        read_thread.start()
        update_thread.start()

        read_thread.join()
        update_thread.join()

        # Both operations should succeed with WAL mode
        assert all(results)

    def test_json_serialization(self, tmp_db):
        """Test that JSON fields are properly serialized/deserialized."""
        # Message with complex metadata and attachments
        message = {
            "id": "msg-json-test",
            "from_project": "/p1",
            "to_project": "/p2",
            "subject": "JSON Test",
            "body": "Testing JSON fields",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "boolean": True,
            },
            "attachments": ["file1.txt", "dir/file2.py", "data.json"],
        }

        # Insert and retrieve
        tmp_db.insert_message(message)
        retrieved = tmp_db.get_message(message["id"])

        # Verify JSON fields properly deserialized
        assert retrieved["metadata"] == message["metadata"]
        assert retrieved["attachments"] == message["attachments"]
        assert isinstance(retrieved["metadata"], dict)
        assert isinstance(retrieved["attachments"], list)

    def test_index_performance(self, tmp_db):
        """Test that indexes improve query performance."""
        # Insert many messages
        for i in range(100):
            msg = {
                "id": f"msg-perf-{i:03d}",
                "from_project": "/p1",
                "to_project": "/p2",
                "subject": f"Message {i}",
                "body": f"Body {i}",
                "status": "unread" if i % 3 == 0 else "read",
                "priority": ["low", "normal", "high", "urgent"][i % 4],
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(hours=i)
                ).isoformat(),
            }
            tmp_db.insert_message(msg)

        # These queries should be fast due to indexes
        import time

        start = time.time()
        tmp_db.list_messages(status="unread")
        status_query_time = time.time() - start

        start = time.time()
        tmp_db.get_high_priority_messages()
        priority_query_time = time.time() - start

        # Should complete quickly (< 100ms even with 100 records)
        assert status_query_time < 0.1
        assert priority_query_time < 0.1
