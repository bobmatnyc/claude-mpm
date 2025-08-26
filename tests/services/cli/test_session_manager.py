"""Tests for SessionManager service.

WHY: Ensures SessionManager correctly handles session lifecycle management,
persistence, validation, and archiving operations.
"""

import gzip
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from claude_mpm.services.cli.session_manager import (
    ISessionManager,
    ManagedSession,
    SessionInfo,
    SessionManager,
    SessionValidation,
)


class TestSessionInfo(unittest.TestCase):
    """Test SessionInfo data class."""

    def test_session_info_creation(self):
        """Test creating SessionInfo with defaults."""
        session = SessionInfo(id="test-id")

        self.assertEqual(session.id, "test-id")
        self.assertEqual(session.context, "default")
        self.assertEqual(session.use_count, 0)
        self.assertEqual(session.agents_run, [])
        self.assertIsInstance(session.created_at, str)
        self.assertIsInstance(session.last_used, str)

    def test_session_info_to_dict(self):
        """Test converting SessionInfo to dictionary."""
        session = SessionInfo(
            id="test-id",
            context="orchestration",
            use_count=5,
            agents_run=[{"agent": "test-agent", "task": "test"}],
        )

        data = session.to_dict()

        self.assertEqual(data["id"], "test-id")
        self.assertEqual(data["context"], "orchestration")
        self.assertEqual(data["use_count"], 5)
        self.assertEqual(len(data["agents_run"]), 1)

    def test_session_info_from_dict(self):
        """Test creating SessionInfo from dictionary."""
        data = {
            "id": "test-id",
            "context": "custom",
            "created_at": "2024-01-01T10:00:00",
            "last_used": "2024-01-01T11:00:00",
            "use_count": 3,
            "agents_run": [{"agent": "agent1"}],
            "metadata": {"key": "value"},
        }

        session = SessionInfo.from_dict(data)

        self.assertEqual(session.id, "test-id")
        self.assertEqual(session.context, "custom")
        self.assertEqual(session.use_count, 3)
        self.assertEqual(session.metadata["key"], "value")


class TestSessionValidation(unittest.TestCase):
    """Test SessionValidation data class."""

    def test_validation_creation(self):
        """Test creating SessionValidation."""
        validation = SessionValidation(valid=True, session_id="test-id")

        self.assertTrue(validation.valid)
        self.assertEqual(validation.session_id, "test-id")
        self.assertFalse(validation.has_issues)

    def test_validation_with_issues(self):
        """Test validation with errors and warnings."""
        validation = SessionValidation(
            valid=False,
            session_id="test-id",
            errors=["Error 1"],
            warnings=["Warning 1"],
        )

        self.assertFalse(validation.valid)
        self.assertTrue(validation.has_issues)
        self.assertEqual(len(validation.errors), 1)
        self.assertEqual(len(validation.warnings), 1)


class TestSessionManager(unittest.TestCase):
    """Test SessionManager implementation."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_dir = Path(self.temp_dir) / "sessions"
        self.manager = SessionManager(session_dir=self.session_dir)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_session(self):
        """Test creating a new session."""
        session = self.manager.create_session(context="test")

        self.assertIsInstance(session, SessionInfo)
        self.assertEqual(session.context, "test")
        self.assertIsNotNone(session.id)

        # Verify session is in cache
        loaded = self.manager.load_session(session.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, session.id)

    def test_create_session_with_options(self):
        """Test creating session with options."""
        options = {"debug": True, "timeout": 30}
        session = self.manager.create_session(context="custom", options=options)

        self.assertEqual(session.context, "custom")
        self.assertEqual(session.metadata, options)

    def test_load_session(self):
        """Test loading an existing session."""
        # Create a session
        session = self.manager.create_session()
        session_id = session.id

        # Load it
        loaded = self.manager.load_session(session_id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, session_id)

    def test_load_nonexistent_session(self):
        """Test loading a session that doesn't exist."""
        loaded = self.manager.load_session("nonexistent-id")
        self.assertIsNone(loaded)

    def test_save_session(self):
        """Test saving session changes."""
        session = self.manager.create_session()
        session.use_count = 10
        session.metadata["updated"] = True

        success = self.manager.save_session(session)

        self.assertTrue(success)

        # Reload and verify changes
        loaded = self.manager.load_session(session.id)
        self.assertEqual(loaded.use_count, 10)
        self.assertTrue(loaded.metadata.get("updated"))

    def test_get_session_info(self):
        """Test getting session metadata."""
        session = self.manager.create_session(context="info-test")

        info = self.manager.get_session_info(session.id)

        self.assertIsNotNone(info)
        self.assertEqual(info["id"], session.id)
        self.assertEqual(info["context"], "info-test")

    def test_validate_valid_session(self):
        """Test validating a valid session."""
        session = self.manager.create_session()

        validation = self.manager.validate_session(session.id)

        self.assertTrue(validation.valid)
        self.assertFalse(validation.has_issues)

    def test_validate_missing_session(self):
        """Test validating a non-existent session."""
        validation = self.manager.validate_session("missing-id")

        self.assertFalse(validation.valid)
        self.assertTrue(validation.has_issues)
        self.assertIn("not found", validation.errors[0])

    def test_validate_old_session(self):
        """Test validating an old session."""
        session = self.manager.create_session()

        # Modify created_at to be 40 days ago
        old_date = (datetime.now() - timedelta(days=40)).isoformat()
        session.created_at = old_date
        self.manager.save_session(session)

        validation = self.manager.validate_session(session.id)

        self.assertFalse(validation.valid)
        self.assertIn("too old", validation.errors[0].lower())

    def test_get_recent_sessions(self):
        """Test getting recent sessions."""
        # Create multiple sessions
        sessions = []
        for i in range(5):
            session = self.manager.create_session(context=f"test-{i}")
            sessions.append(session)

        recent = self.manager.get_recent_sessions(limit=3)

        self.assertEqual(len(recent), 3)
        # Should be sorted by last_used (most recent first)
        self.assertEqual(recent[0].id, sessions[-1].id)

    def test_get_recent_sessions_by_context(self):
        """Test filtering recent sessions by context."""
        # Create sessions with different contexts
        self.manager.create_session(context="default")
        self.manager.create_session(context="orchestration")
        self.manager.create_session(context="default")

        recent = self.manager.get_recent_sessions(context="default")

        self.assertEqual(len(recent), 2)
        for session in recent:
            self.assertEqual(session.context, "default")

    def test_get_last_interactive_session(self):
        """Test getting last interactive session."""
        # Create non-default session
        self.manager.create_session(context="orchestration")

        # Create default sessions
        self.manager.create_session(context="default")
        session2 = self.manager.create_session(context="default")

        last_id = self.manager.get_last_interactive_session()

        self.assertEqual(last_id, session2.id)

    def test_record_agent_use(self):
        """Test recording agent activity."""
        session = self.manager.create_session()

        self.manager.record_agent_use(
            session.id, agent="test-agent", task="Process data"
        )

        # Reload and check
        loaded = self.manager.load_session(session.id)

        self.assertEqual(len(loaded.agents_run), 1)
        self.assertEqual(loaded.agents_run[0]["agent"], "test-agent")
        self.assertEqual(loaded.agents_run[0]["task"], "Process data")
        self.assertEqual(loaded.use_count, 1)

    def test_record_agent_use_truncates_long_task(self):
        """Test that long task descriptions are truncated."""
        session = self.manager.create_session()
        long_task = "x" * 200

        self.manager.record_agent_use(session.id, "agent", long_task)

        loaded = self.manager.load_session(session.id)
        self.assertEqual(len(loaded.agents_run[0]["task"]), 100)

    def test_cleanup_old_sessions(self):
        """Test cleaning up old sessions."""
        # Create old session
        old_session = self.manager.create_session()
        old_date = (datetime.now() - timedelta(hours=48)).isoformat()
        old_session.created_at = old_date
        self.manager.save_session(old_session)

        # Create recent session
        recent_session = self.manager.create_session()

        # Cleanup with 24 hour threshold
        cleaned = self.manager.cleanup_old_sessions(max_age_hours=24, archive=False)

        self.assertEqual(cleaned, 1)
        self.assertIsNone(self.manager.load_session(old_session.id))
        self.assertIsNotNone(self.manager.load_session(recent_session.id))

    def test_archive_sessions(self):
        """Test archiving sessions."""
        sessions = []
        for i in range(3):
            session = self.manager.create_session(context=f"archive-{i}")
            sessions.append(session.id)

        success = self.manager.archive_sessions(sessions[:2])

        self.assertTrue(success)

        # Check archive was created
        archive_dir = self.session_dir.parent / "archives" / "sessions"
        self.assertTrue(archive_dir.exists())

        # Find archive file
        archives = list(archive_dir.glob("*.json.gz"))
        self.assertEqual(len(archives), 1)

        # Verify archive contents
        with gzip.open(archives[0], "rt") as f:
            archived = json.load(f)

        self.assertEqual(len(archived), 2)
        archived_ids = [s["id"] for s in archived]
        self.assertIn(sessions[0], archived_ids)
        self.assertIn(sessions[1], archived_ids)

    def test_cleanup_with_archive(self):
        """Test cleanup with archiving enabled."""
        # Create old session
        old_session = self.manager.create_session()
        old_date = (datetime.now() - timedelta(hours=48)).isoformat()
        old_session.created_at = old_date
        self.manager.save_session(old_session)

        # Cleanup with archiving
        cleaned = self.manager.cleanup_old_sessions(max_age_hours=24, archive=True)

        self.assertEqual(cleaned, 1)

        # Verify archive was created
        archive_dir = self.session_dir.parent / "archives" / "sessions"
        archives = list(archive_dir.glob("*.json.gz"))
        self.assertGreater(len(archives), 0)

    def test_persistence_across_instances(self):
        """Test session persistence across manager instances."""
        # Create session with first manager
        session = self.manager.create_session(context="persist-test")
        session_id = session.id

        # Create new manager instance
        new_manager = SessionManager(session_dir=self.session_dir)

        # Load session with new manager
        loaded = new_manager.load_session(session_id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.context, "persist-test")

    def test_corrupt_session_file_recovery(self):
        """Test recovery from corrupt session file."""
        # Create valid session
        self.manager.create_session()

        # Corrupt the session file
        session_file = self.session_dir / "active_sessions.json"
        with open(session_file, "w") as f:
            f.write("invalid json{")

        # Create new manager (should handle corruption)
        new_manager = SessionManager(session_dir=self.session_dir)

        # Should have empty sessions after corruption
        self.assertEqual(len(new_manager._sessions_cache), 0)

        # Should still be able to create new sessions
        new_session = new_manager.create_session()
        self.assertIsNotNone(new_session)


class TestManagedSession(unittest.TestCase):
    """Test ManagedSession context manager."""

    def setUp(self):
        """Set up test environment."""
        self.manager = MagicMock(spec=ISessionManager)
        self.test_session = SessionInfo(id="test-id", context="managed")

    def test_managed_session_creates_and_saves(self):
        """Test context manager creates and saves session."""
        self.manager.create_session.return_value = self.test_session

        with ManagedSession(self.manager, context="test") as session:
            self.assertEqual(session.id, "test-id")
            self.manager.create_session.assert_called_once_with("test", None)

        # Verify session was saved on exit
        self.manager.save_session.assert_called_once()
        saved_session = self.manager.save_session.call_args[0][0]
        self.assertEqual(saved_session.id, "test-id")

    def test_managed_session_with_options(self):
        """Test context manager with options."""
        options = {"timeout": 60}
        self.manager.create_session.return_value = self.test_session

        with ManagedSession(self.manager, context="test", options=options):
            self.manager.create_session.assert_called_once_with("test", options)

    def test_managed_session_updates_last_used(self):
        """Test context manager updates last_used on exit."""
        self.manager.create_session.return_value = self.test_session
        original_time = self.test_session.last_used

        with ManagedSession(self.manager, context="test"):
            pass

        # Verify last_used was updated
        saved_session = self.manager.save_session.call_args[0][0]
        self.assertNotEqual(saved_session.last_used, original_time)

    def test_managed_session_handles_exception(self):
        """Test context manager handles exceptions properly."""
        self.manager.create_session.return_value = self.test_session

        try:
            with ManagedSession(self.manager, context="test"):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Session should still be saved even with exception
        self.manager.save_session.assert_called_once()


class TestInterfaceCompliance(unittest.TestCase):
    """Test that SessionManager properly implements ISessionManager."""

    def test_session_manager_implements_interface(self):
        """Test SessionManager implements all required methods."""
        temp_dir = tempfile.mkdtemp()
        try:
            manager = SessionManager(session_dir=Path(temp_dir))

            # Verify it's an instance of the interface
            self.assertIsInstance(manager, ISessionManager)

            # Verify all interface methods are implemented
            interface_methods = [
                "create_session",
                "load_session",
                "save_session",
                "get_session_info",
                "validate_session",
                "get_recent_sessions",
                "get_last_interactive_session",
                "record_agent_use",
                "cleanup_old_sessions",
                "archive_sessions",
            ]

            for method in interface_methods:
                self.assertTrue(
                    hasattr(manager, method),
                    f"SessionManager missing required method: {method}",
                )
                self.assertTrue(
                    callable(getattr(manager, method)),
                    f"SessionManager.{method} is not callable",
                )
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
