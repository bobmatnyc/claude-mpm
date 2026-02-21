"""Tests for TaskInjector module."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from claude_mpm.services.communication.task_injector import PRIORITY_MAP, TaskInjector


@pytest.fixture
def temp_tasks_dir(tmp_path):
    """Create a temporary tasks directory for testing."""
    tasks_dir = tmp_path / ".claude" / "tasks"
    tasks_dir.mkdir(parents=True)
    return tasks_dir


@pytest.fixture
def injector(temp_tasks_dir):
    """Create TaskInjector with temp directory."""
    return TaskInjector(tasks_dir=temp_tasks_dir)


def test_inject_message_task_creates_file(injector, temp_tasks_dir):
    """Verify JSON file written to tasks dir."""
    task_file = injector.inject_message_task(
        message_id="test-123",
        from_project="/home/user/project-a",
        subject="Test Message",
        body="This is a test message body",
        priority="high",
        from_agent="engineer",
        message_type="task",
    )

    # Verify file created
    assert task_file.exists()
    assert task_file.name == "msg-test-123.json"
    assert task_file.parent == temp_tasks_dir

    # Verify JSON content
    task_data = json.loads(task_file.read_text())
    assert task_data["id"] == "msg-test-123"
    assert "Test Message" in task_data["title"]
    assert "project-a" in task_data["title"]
    assert task_data["status"] == "pending"
    assert task_data["priority"] == "high"  # High message priority → high task priority
    assert "This is a test message body" in task_data["description"]
    assert task_data["metadata"]["source"] == "mpm-messaging"
    assert task_data["metadata"]["message_id"] == "test-123"
    assert task_data["metadata"]["message_type"] == "task"


def test_inject_message_task_correct_format(injector, temp_tasks_dir):
    """Verify JSON schema matches Claude Code format."""
    task_file = injector.inject_message_task(
        message_id="test-456",
        from_project="/usr/local/project-b",
        subject="Important Request",
        body="Please review the code",
        priority="urgent",
        from_agent="pm",
        message_type="request",
    )

    task_data = json.loads(task_file.read_text())

    # Check required fields for Claude Code compatibility
    assert "id" in task_data
    assert "title" in task_data
    assert "description" in task_data
    assert "status" in task_data
    assert "priority" in task_data
    assert "created_at" in task_data

    # Verify timestamp format (ISO 8601)
    created_at = datetime.fromisoformat(task_data["created_at"])
    assert created_at.tzinfo is not None  # Should have timezone


def test_task_exists_true(injector, temp_tasks_dir):
    """Verify detection of existing task."""
    # Create task
    injector.inject_message_task(
        message_id="exists-123",
        from_project="/home/test",
        subject="Test",
        body="Body",
    )

    # Check it exists
    assert injector.task_exists("exists-123") is True


def test_task_exists_false(injector):
    """Verify false for non-existent task."""
    assert injector.task_exists("nonexistent-456") is False


def test_remove_task(injector, temp_tasks_dir):
    """Verify task file deletion."""
    # Create task
    injector.inject_message_task(
        message_id="remove-123",
        from_project="/home/test",
        subject="Test",
        body="Body",
    )

    # Verify it exists
    assert injector.task_exists("remove-123")

    # Remove it
    result = injector.remove_task("remove-123")
    assert result is True

    # Verify it's gone
    assert not injector.task_exists("remove-123")


def test_remove_task_nonexistent(injector):
    """Returns False gracefully."""
    result = injector.remove_task("nonexistent-789")
    assert result is False


def test_cleanup_completed_tasks(injector, temp_tasks_dir):
    """Only removes completed/done status."""
    # Create tasks with different statuses
    for status, msg_id in [
        ("pending", "msg-1"),
        ("completed", "msg-2"),
        ("done", "msg-3"),
        ("in-progress", "msg-4"),
    ]:
        task_file = temp_tasks_dir / f"{msg_id}.json"
        task_file.write_text(json.dumps({"id": msg_id, "status": status}))

    # Run cleanup
    removed_count = injector.cleanup_completed_tasks()

    # Verify only completed/done were removed
    assert removed_count == 2
    assert (temp_tasks_dir / "msg-1.json").exists()  # pending kept
    assert not (temp_tasks_dir / "msg-2.json").exists()  # completed removed
    assert not (temp_tasks_dir / "msg-3.json").exists()  # done removed
    assert (temp_tasks_dir / "msg-4.json").exists()  # in-progress kept


def test_cleanup_skips_pending_tasks(injector, temp_tasks_dir):
    """Pending tasks preserved."""
    # Create only pending tasks
    for i in range(3):
        task_file = temp_tasks_dir / f"msg-pending-{i}.json"
        task_file.write_text(
            json.dumps({"id": f"msg-pending-{i}", "status": "pending"})
        )

    # Run cleanup
    removed_count = injector.cleanup_completed_tasks()

    # Verify none were removed
    assert removed_count == 0
    for i in range(3):
        assert (temp_tasks_dir / f"msg-pending-{i}.json").exists()


def test_deduplication(injector, temp_tasks_dir):
    """Second inject for same message_id is no-op."""
    # First injection
    task_file1 = injector.inject_message_task(
        message_id="dedup-123",
        from_project="/home/test",
        subject="Original",
        body="Original body",
    )

    original_content = task_file1.read_text()

    # Check exists
    assert injector.task_exists("dedup-123")

    # Second injection with different content
    task_file2 = injector.inject_message_task(
        message_id="dedup-123",
        from_project="/home/test",
        subject="Changed",
        body="Changed body",
    )

    # Files should be the same
    assert task_file1 == task_file2

    # Content should be updated (overwritten)
    new_content = task_file2.read_text()
    assert "Changed" in new_content
    assert original_content != new_content


def test_priority_mapping(injector, temp_tasks_dir):
    """All priority levels map correctly."""
    test_cases = [
        ("urgent", "high"),
        ("high", "high"),
        ("normal", "medium"),
        ("low", "low"),
        ("unknown", "medium"),  # Default case
    ]

    for message_priority, expected_task_priority in test_cases:
        task_file = injector.inject_message_task(
            message_id=f"priority-{message_priority}",
            from_project="/home/test",
            subject="Test",
            body="Body",
            priority=message_priority,
        )

        task_data = json.loads(task_file.read_text())
        assert task_data["priority"] == expected_task_priority, (
            f"Failed for {message_priority}"
        )


def test_list_message_tasks(injector, temp_tasks_dir):
    """Returns all msg-* tasks."""
    # Create some message tasks
    for i in range(3):
        injector.inject_message_task(
            message_id=f"list-{i}",
            from_project="/home/test",
            subject=f"Subject {i}",
            body=f"Body {i}",
        )

    # Create non-message task (should be ignored)
    other_task = temp_tasks_dir / "regular-task.json"
    other_task.write_text(json.dumps({"id": "regular-task", "title": "Regular"}))

    # List message tasks
    tasks = injector.list_message_tasks()

    # Verify only message tasks returned
    assert len(tasks) == 3
    task_ids = [t["id"] for t in tasks]
    assert "msg-list-0" in task_ids
    assert "msg-list-1" in task_ids
    assert "msg-list-2" in task_ids
    assert "regular-task" not in task_ids


def test_custom_tasks_dir(tmp_path):
    """Constructor accepts override path."""
    custom_dir = tmp_path / "custom" / "location"
    injector = TaskInjector(tasks_dir=custom_dir)

    # Verify directory created
    assert custom_dir.exists()
    assert custom_dir.is_dir()

    # Verify tasks go to custom location
    task_file = injector.inject_message_task(
        message_id="custom-123",
        from_project="/home/test",
        subject="Test",
        body="Body",
    )

    assert task_file.parent == custom_dir


def test_format_description_includes_all_fields(injector, temp_tasks_dir):
    """Description contains all message details."""
    task_file = injector.inject_message_task(
        message_id="desc-123",
        from_project="/home/user/awesome-project",
        subject="Review PR #456",
        body="Please review my pull request for the new feature.",
        priority="urgent",
        from_agent="engineer",
        message_type="request",
    )

    task_data = json.loads(task_file.read_text())
    description = task_data["description"]

    # Verify all fields are in description
    assert "/home/user/awesome-project" in description
    assert "engineer" in description
    assert "request" in description
    assert "urgent" in description
    assert "Review PR #456" in description
    assert "Please review my pull request" in description
    assert "desc-123" in description
    assert "claude-mpm message read" in description
    assert "claude-mpm message reply" in description


def test_message_type_emojis(injector, temp_tasks_dir):
    """Different message types get appropriate emojis."""
    test_cases = [
        ("task", "📋"),
        ("request", "❓"),
        ("notification", "📢"),
        ("reply", "💬"),
        ("unknown", "📬"),  # Default
    ]

    for message_type, expected_emoji in test_cases:
        task_file = injector.inject_message_task(
            message_id=f"emoji-{message_type}",
            from_project="/home/test",
            subject="Test",
            body="Body",
            message_type=message_type,
        )

        task_data = json.loads(task_file.read_text())
        assert expected_emoji in task_data["description"], f"Failed for {message_type}"
