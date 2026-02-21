"""
Integration tests for MessageService with SQLite backend.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from claude_mpm.services.communication.message_service import MessageService


@pytest.fixture
def tmp_projects(tmp_path):
    """Create two temporary project directories with isolated registry."""
    project1 = tmp_path / "project1"
    project2 = tmp_path / "project2"
    project1.mkdir(parents=True)
    project2.mkdir(parents=True)
    # Use isolated registry to avoid polluting global session-registry.db
    registry = tmp_path / "test-registry.db"
    return project1, project2, registry


class TestMessageServiceIntegration:
    """Test MessageService with database backend."""

    def test_send_and_receive_message(self, tmp_projects):
        """Test sending a message from one project to another."""
        project1, project2, registry = tmp_projects

        # Create services for both projects
        service1 = MessageService(project1, registry_path=registry)
        service2 = MessageService(project2, registry_path=registry)

        # Send message from project1 to project2
        message = service1.send_message(
            to_project=str(project2),
            to_agent="engineer",
            message_type="task",
            subject="Test Task",
            body="Please complete this test task.",
            priority="high",
            from_agent="pm",
            attachments=["file1.txt", "file2.py"],
            metadata={"key": "value"},
        )

        assert message is not None
        assert message.subject == "Test Task"
        assert message.status == "sent"

        # Check that project2 received the message
        messages = service2.list_messages(status="unread")
        assert len(messages) == 1

        received = messages[0]
        assert received.subject == "Test Task"
        assert received.body == "Please complete this test task."
        assert received.from_project == str(project1)
        assert received.to_agent == "engineer"
        assert received.priority == "high"
        assert received.attachments == ["file1.txt", "file2.py"]
        assert received.metadata == {"key": "value"}

    def test_read_message_marks_as_read(self, tmp_projects):
        """Test that reading a message marks it as read."""
        project1, project2, registry = tmp_projects

        service1 = MessageService(project1, registry_path=registry)
        service2 = MessageService(project2, registry_path=registry)

        # Send message
        message = service1.send_message(
            to_project=str(project2),
            to_agent="pm",
            message_type="notification",
            subject="Test Notification",
            body="This is a test.",
        )

        # Initially unread
        assert service2.get_unread_count() == 1

        # Read the message
        read_message = service2.read_message(message.id)
        assert read_message is not None
        assert read_message.status == "read"

        # Now no unread messages
        assert service2.get_unread_count() == 0

    def test_archive_message(self, tmp_projects):
        """Test archiving a message."""
        project1, project2, registry = tmp_projects

        service1 = MessageService(project1, registry_path=registry)
        service2 = MessageService(project2, registry_path=registry)

        # Send message
        message = service1.send_message(
            to_project=str(project2),
            to_agent="pm",
            message_type="notification",
            subject="Test Archive",
            body="Archive this.",
        )

        # Archive the message
        success = service2.archive_message(message.id)
        assert success is True

        # Should not appear in unread or read lists
        unread = service2.list_messages(status="unread")
        read = service2.list_messages(status="read")
        assert len(unread) == 0
        assert len(read) == 0

        # Should appear in archived list
        archived = service2.list_messages(status="archived")
        assert len(archived) == 1
        assert archived[0].id == message.id

    def test_reply_to_message(self, tmp_projects):
        """Test replying to a message."""
        project1, project2, registry = tmp_projects

        service1 = MessageService(project1, registry_path=registry)
        service2 = MessageService(project2, registry_path=registry)

        # Send original message
        original = service1.send_message(
            to_project=str(project2),
            to_agent="engineer",
            message_type="request",
            subject="Need Help",
            body="Can you help with this?",
            from_agent="pm",
        )

        # Reply from project2
        reply = service2.reply_to_message(
            original_message_id=original.id,
            subject="Re: Need Help",
            body="Sure, I can help!",
            from_agent="engineer",
        )

        assert reply is not None
        assert reply.type == "reply"
        assert reply.to_project == str(project1)
        assert reply.to_agent == "pm"
        assert reply.subject == "Re: Need Help"

        # Check that project1 received the reply
        messages = service1.list_messages()
        assert len(messages) >= 1  # May include sent message

        # Find the reply
        replies = [m for m in messages if m.type == "reply"]
        assert len(replies) == 1
        assert replies[0].body == "Sure, I can help!"

    def test_filter_messages_by_agent(self, tmp_projects):
        """Test filtering messages by target agent."""
        project1, project2, registry = tmp_projects

        service1 = MessageService(project1, registry_path=registry)
        service2 = MessageService(project2, registry_path=registry)

        # Send messages to different agents
        service1.send_message(
            to_project=str(project2),
            to_agent="pm",
            message_type="notification",
            subject="For PM",
            body="PM message",
        )

        service1.send_message(
            to_project=str(project2),
            to_agent="engineer",
            message_type="task",
            subject="For Engineer",
            body="Engineer task",
        )

        service1.send_message(
            to_project=str(project2),
            to_agent="qa",
            message_type="request",
            subject="For QA",
            body="QA request",
        )

        # Filter by agent
        pm_messages = service2.list_messages(agent="pm")
        assert len(pm_messages) == 1
        assert pm_messages[0].subject == "For PM"

        engineer_messages = service2.list_messages(agent="engineer")
        assert len(engineer_messages) == 1
        assert engineer_messages[0].subject == "For Engineer"

        qa_messages = service2.list_messages(agent="qa")
        assert len(qa_messages) == 1
        assert qa_messages[0].subject == "For QA"

    def test_high_priority_messages(self, tmp_projects):
        """Test getting high priority messages."""
        project1, project2, registry = tmp_projects

        service1 = MessageService(project1, registry_path=registry)
        service2 = MessageService(project2, registry_path=registry)

        # Send messages with different priorities
        service1.send_message(
            to_project=str(project2),
            to_agent="pm",
            message_type="notification",
            subject="Low Priority",
            body="Not urgent",
            priority="low",
        )

        service1.send_message(
            to_project=str(project2),
            to_agent="pm",
            message_type="task",
            subject="High Priority",
            body="Important task",
            priority="high",
        )

        service1.send_message(
            to_project=str(project2),
            to_agent="pm",
            message_type="request",
            subject="Urgent",
            body="Very urgent!",
            priority="urgent",
        )

        service1.send_message(
            to_project=str(project2),
            to_agent="pm",
            message_type="notification",
            subject="Normal Priority",
            body="Regular message",
            priority="normal",
        )

        # Get high priority messages
        high_priority = service2.get_high_priority_messages()
        assert len(high_priority) == 2  # urgent and high

        # Verify ordering (urgent first)
        assert high_priority[0].priority == "urgent"
        assert high_priority[1].priority == "high"

    def test_session_registry(self, tmp_projects):
        """Test that sessions are registered in global registry."""
        project1, project2, registry = tmp_projects

        # Create services (automatically registers sessions)
        service1 = MessageService(project1, registry_path=registry)
        service2 = MessageService(project2, registry_path=registry)

        # Check global registry
        sessions = service1.global_registry.list_active_sessions()

        # Should have at least 2 sessions
        assert len(sessions) >= 2

        # Find our project sessions
        project_paths = {str(project1), str(project2)}
        found_sessions = [s for s in sessions if s["project_path"] in project_paths]
        assert len(found_sessions) == 2

        # Verify session data
        for session in found_sessions:
            assert session["status"] == "active"
            assert session["project_name"] in ["project1", "project2"]

    def test_database_persistence(self, tmp_projects):
        """Test that messages persist across service instances."""
        project1, project2, registry = tmp_projects

        # First service instance sends message
        service1_a = MessageService(project1, registry_path=registry)
        service2_a = MessageService(project2, registry_path=registry)

        message = service1_a.send_message(
            to_project=str(project2),
            to_agent="pm",
            message_type="notification",
            subject="Persistent Message",
            body="This should persist",
        )

        # Create new service instances (simulating restart)
        service1_b = MessageService(project1, registry_path=registry)
        service2_b = MessageService(project2, registry_path=registry)

        # Should still see the message
        messages = service2_b.list_messages()
        assert len(messages) == 1
        assert messages[0].id == message.id
        assert messages[0].subject == "Persistent Message"

        # Sent message should be in project1's database
        # (Note: This assumes we might add a list_sent_messages method)
        # For now, we can verify by checking the database directly
        sent_msg = service1_b.messaging_db.get_message(message.id)
        assert sent_msg is not None
        assert sent_msg["status"] == "sent"
