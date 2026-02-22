"""
Test the Huey-based message bus implementation.
"""

import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.communication.message_bus import MessageBus
from claude_mpm.services.communication.message_service import MessageService
from claude_mpm.services.communication.messaging_db import MessagingDatabase


@pytest.fixture
def temp_home(tmp_path):
    """Create a temporary home directory for testing."""
    return tmp_path


@pytest.fixture
def mock_home(temp_home, monkeypatch):
    """Mock Path.home() to use temp directory."""
    # Reset MessageBus singleton before test
    from claude_mpm.services.communication.message_bus import MessageBus

    MessageBus._instance = None
    MessageBus._huey = None

    monkeypatch.setattr(Path, "home", lambda: temp_home)
    return temp_home


@pytest.fixture
def project_root(tmp_path):
    """Create a temporary project root."""
    project = tmp_path / "test-project"
    project.mkdir()
    return project


@pytest.fixture
def target_project(tmp_path):
    """Create a target project for messaging."""
    project = tmp_path / "target-project"
    project.mkdir()
    return project


class TestMessageBus:
    """Test the MessageBus class."""

    def test_singleton_pattern(self, mock_home):
        """Test that MessageBus follows singleton pattern."""
        bus1 = MessageBus()
        bus2 = MessageBus()
        assert bus1 is bus2
        assert bus1.huey is bus2.huey

    def test_initialization(self, mock_home):
        """Test MessageBus initialization."""
        bus = MessageBus()

        # Check Huey instance
        assert bus.huey is not None
        assert bus.huey.name == "claude_mpm_messages"

        # Check that queue database path is set correctly
        # The path should be under mocked home
        assert ".claude-mpm/message_queue.db" in str(bus.huey.storage.filename)

    def test_enqueue_message(self, mock_home):
        """Test message enqueueing."""
        bus = MessageBus()

        message_data = {
            "id": "test-msg-001",
            "from_project": "/path/to/project1",
            "to_project": "/path/to/project2",
            "from_agent": "pm",
            "to_agent": "engineer",
            "type": "task",
            "priority": "high",
            "subject": "Test Message",
            "body": "This is a test",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        task = bus.enqueue_message(message_data)
        assert task is not None


class TestMessageServiceWithBus:
    """Test MessageService with Huey bus integration."""

    def test_shared_database(self, mock_home, project_root):
        """Test that MessageService uses shared database."""
        service = MessageService(project_root)

        # Check it uses shared database, not per-project
        expected_db = mock_home / ".claude-mpm" / "messaging.db"
        assert service.messaging_db_path == expected_db
        assert expected_db.exists()

    def test_send_message_to_other_project(
        self, mock_home, project_root, target_project
    ):
        """Test sending message to another project."""
        service = MessageService(project_root)

        # Send a message
        message = service.send_message(
            to_project=str(target_project),
            to_agent="engineer",
            message_type="task",
            subject="Test Task",
            body="Please complete this task",
            priority="high",
            from_agent="pm",
        )

        assert message.id.startswith("msg-")
        assert message.from_project == str(project_root)
        assert message.to_project == str(target_project)
        assert message.status == "sent"

    def test_send_self_message(self, mock_home, project_root):
        """Test sending message to same project."""
        service = MessageService(project_root)

        # Send a self-message
        message = service.send_message(
            to_project=str(project_root),  # Same as from_project
            to_agent="qa",
            message_type="notification",
            subject="Self Notification",
            body="This is a self-message",
            from_agent="pm",
        )

        assert message.from_project == str(project_root)
        assert message.to_project == str(project_root)

        # Self-messages should appear in inbox immediately
        messages = service.list_messages(status="unread")
        assert len(messages) == 1
        assert messages[0].subject == "Self Notification"

    def test_list_messages_filters_by_project(
        self, mock_home, project_root, target_project
    ):
        """Test that list_messages only shows messages for current project."""
        # Create services for both projects
        service1 = MessageService(project_root)
        service2 = MessageService(target_project)

        # Project 1 sends to Project 2
        service1.send_message(
            to_project=str(target_project),
            to_agent="pm",
            message_type="task",
            subject="Message for Project 2",
            body="This should only appear in project 2",
        )

        # Project 2 sends to Project 1
        service2.send_message(
            to_project=str(project_root),
            to_agent="pm",
            message_type="task",
            subject="Message for Project 1",
            body="This should only appear in project 1",
        )

        # Each project should only see its own messages
        messages1 = service1.list_messages()
        messages2 = service2.list_messages()

        # Filter out sent messages, only check received
        received1 = [m for m in messages1 if m.to_project == str(project_root)]
        received2 = [m for m in messages2 if m.to_project == str(target_project)]

        assert len(received1) == 1
        assert received1[0].subject == "Message for Project 1"

        assert len(received2) == 1
        assert received2[0].subject == "Message for Project 2"

    def test_read_message_marks_as_read(self, mock_home, project_root):
        """Test that reading a message marks it as read."""
        service = MessageService(project_root)

        # Send a self-message
        sent = service.send_message(
            to_project=str(project_root),
            to_agent="pm",
            message_type="notification",
            subject="Test Read",
            body="Mark me as read",
        )

        # Initially unread
        unread_count = service.get_unread_count()
        assert unread_count == 1

        # Read the message
        read_msg = service.read_message(sent.id)
        assert read_msg is not None
        assert read_msg.status == "read"

        # Should now be marked as read
        unread_count = service.get_unread_count()
        assert unread_count == 0

    def test_high_priority_filtering(self, mock_home, project_root):
        """Test high priority message filtering."""
        service = MessageService(project_root)

        # Send messages with different priorities
        priorities = ["low", "normal", "high", "urgent"]
        for priority in priorities:
            service.send_message(
                to_project=str(project_root),
                to_agent="pm",
                message_type="task",
                subject=f"{priority.title()} Priority Task",
                body=f"This is a {priority} priority task",
                priority=priority,
            )

        # Get high priority messages
        high_priority = service.get_high_priority_messages()

        # Should only include high and urgent
        assert len(high_priority) == 2
        subjects = [m.subject for m in high_priority]
        assert "High Priority Task" in subjects
        assert "Urgent Priority Task" in subjects
        assert "Normal Priority Task" not in subjects
        assert "Low Priority Task" not in subjects


class TestMessagingDatabase:
    """Test the MessagingDatabase with project filtering."""

    def test_project_filtering_methods(self, mock_home):
        """Test new project-specific filtering methods."""
        db_path = mock_home / ".claude-mpm" / "test.db"
        db = MessagingDatabase(db_path)

        # Insert messages for different projects
        projects = ["/project1", "/project2", "/project3"]

        for i, project in enumerate(projects):
            db.insert_message(
                {
                    "id": f"msg-{i}",
                    "from_project": "/source",
                    "to_project": project,
                    "from_agent": "pm",
                    "to_agent": "engineer",
                    "type": "task",
                    "priority": "normal" if i < 2 else "high",
                    "subject": f"Task for {project}",
                    "body": f"Body for {project}",
                    "status": "unread",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        # Test get_messages_for_project
        project1_msgs = db.get_messages_for_project("/project1")
        assert len(project1_msgs) == 1
        assert project1_msgs[0]["subject"] == "Task for /project1"

        # Test get_unread_count_for_project
        count = db.get_unread_count_for_project("/project2")
        assert count == 1

        # Test get_high_priority_messages_for_project
        high_priority = db.get_high_priority_messages_for_project("/project3")
        assert len(high_priority) == 1
        assert high_priority[0]["priority"] == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
