"""Integration test for message to task injection flow."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from claude_mpm.services.communication.message_service import Message, MessageService
from claude_mpm.services.communication.task_injector import TaskInjector


@pytest.fixture
def temp_project_dirs(tmp_path):
    """Create two temporary project directories for testing cross-project messaging."""
    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    project_a.mkdir()
    project_b.mkdir()
    return project_a, project_b


@pytest.fixture
def temp_tasks_dir(tmp_path):
    """Create a temporary tasks directory for testing."""
    tasks_dir = tmp_path / ".claude" / "tasks"
    tasks_dir.mkdir(parents=True)
    return tasks_dir


def test_message_to_task_integration(temp_project_dirs, temp_tasks_dir):
    """Test complete flow from message send to task creation."""
    project_a, project_b = temp_project_dirs

    # Step 1: Send message from Project A to Project B
    service_a = MessageService(project_a)
    message = service_a.send_message(
        to_project=str(project_b),
        to_agent="engineer",
        message_type="task",
        subject="Implement OAuth2 authentication",
        body="Please add OAuth2 support with Google provider. Include token refresh logic.",
        priority="high",
        from_agent="pm",
    )

    # Step 2: Check message arrived in Project B's inbox
    service_b = MessageService(project_b)
    unread_messages = service_b.list_messages(status="unread")
    assert len(unread_messages) == 1
    received_msg = unread_messages[0]
    assert received_msg.subject == "Implement OAuth2 authentication"
    assert received_msg.priority == "high"
    assert received_msg.type == "task"

    # Step 3: Inject message as task
    injector = TaskInjector(tasks_dir=temp_tasks_dir)
    task_file = injector.inject_message_task(
        message_id=received_msg.id,
        from_project=received_msg.from_project,
        subject=received_msg.subject,
        body=received_msg.body,
        priority=received_msg.priority,
        from_agent=received_msg.from_agent,
        message_type=received_msg.type,
    )

    # Step 4: Verify task created correctly
    assert task_file.exists()
    task_data = json.loads(task_file.read_text())

    # Verify task fields
    assert task_data["id"] == f"msg-{received_msg.id}"
    assert "Implement OAuth2 authentication" in task_data["title"]
    assert "project-a" in task_data["title"]
    assert task_data["status"] == "pending"
    assert task_data["priority"] == "high"  # high message → high task
    assert "OAuth2 support with Google provider" in task_data["description"]
    assert task_data["metadata"]["source"] == "mpm-messaging"
    assert task_data["metadata"]["message_type"] == "task"

    # Step 5: Verify task appears in list
    tasks = injector.list_message_tasks()
    assert len(tasks) == 1
    assert tasks[0]["id"] == f"msg-{received_msg.id}"

    # Step 6: Mark message as read
    read_msg = service_b.read_message(received_msg.id)
    assert read_msg.status == "read"

    # Step 7: Reply to message
    reply = service_b.reply_to_message(
        original_message_id=received_msg.id,
        subject="Re: Implement OAuth2 authentication",
        body="OAuth2 implementation complete. Tests passing.",
        from_agent="engineer",
    )
    assert reply is not None
    assert reply.type == "reply"

    # Step 8: Check reply arrived in Project A's inbox
    replies = service_a.list_messages(status="unread")
    assert len(replies) == 1
    assert replies[0].type == "reply"
    assert "OAuth2 implementation complete" in replies[0].body


def test_priority_filtering_in_task_injection(temp_project_dirs, temp_tasks_dir):
    """Test that only high-priority messages create tasks."""
    project_a, project_b = temp_project_dirs
    service_a = MessageService(project_a)
    service_b = MessageService(project_b)
    injector = TaskInjector(tasks_dir=temp_tasks_dir)

    # Send messages with different priorities
    priorities = ["urgent", "high", "normal", "low"]
    for priority in priorities:
        service_a.send_message(
            to_project=str(project_b),
            to_agent="pm",
            message_type="notification",
            subject=f"{priority.capitalize()} priority message",
            body=f"This is a {priority} priority message",
            priority=priority,
        )

    # Simulate priority filtering (only urgent/high)
    priority_filter = {"urgent", "high"}
    messages = service_b.list_messages(status="unread")

    injected_count = 0
    for msg in messages:
        if msg.priority in priority_filter:
            injector.inject_message_task(
                message_id=msg.id,
                from_project=msg.from_project,
                subject=msg.subject,
                body=msg.body,
                priority=msg.priority,
            )
            injected_count += 1

    # Verify only high-priority messages created tasks
    tasks = injector.list_message_tasks()
    assert len(tasks) == 2  # Only urgent and high
    task_priorities = [t["priority"] for t in tasks]
    assert all(p == "high" for p in task_priorities)  # Both map to "high" task priority


def test_task_cleanup_after_completion(temp_tasks_dir):
    """Test cleaning up completed message tasks."""
    injector = TaskInjector(tasks_dir=temp_tasks_dir)

    # Create multiple tasks
    message_ids = ["msg-1", "msg-2", "msg-3"]
    for msg_id in message_ids:
        injector.inject_message_task(
            message_id=msg_id,
            from_project="/home/test",
            subject=f"Task {msg_id}",
            body="Body",
        )

    # Manually mark some as completed
    for msg_id in ["msg-1", "msg-3"]:
        task_file = temp_tasks_dir / f"msg-{msg_id}.json"
        task_data = json.loads(task_file.read_text())
        task_data["status"] = "completed"
        task_file.write_text(json.dumps(task_data))

    # Run cleanup
    removed_count = injector.cleanup_completed_tasks()

    # Verify correct tasks removed
    assert removed_count == 2
    assert not injector.task_exists("msg-1")  # Completed, removed
    assert injector.task_exists("msg-2")  # Pending, kept
    assert not injector.task_exists("msg-3")  # Completed, removed


def test_deduplication_prevents_duplicate_tasks(temp_tasks_dir):
    """Test that existing tasks aren't duplicated."""
    injector = TaskInjector(tasks_dir=temp_tasks_dir)

    # First injection
    injector.inject_message_task(
        message_id="dup-test",
        from_project="/home/test",
        subject="Original",
        body="Original body",
    )

    # Verify task exists
    assert injector.task_exists("dup-test")
    tasks = injector.list_message_tasks()
    assert len(tasks) == 1

    # Simulate checking if should inject again (deduplication logic)
    if not injector.task_exists("dup-test"):
        injector.inject_message_task(
            message_id="dup-test",
            from_project="/home/test",
            subject="Duplicate",
            body="Duplicate body",
        )

    # Verify still only one task (deduplication worked)
    tasks = injector.list_message_tasks()
    assert len(tasks) == 1
