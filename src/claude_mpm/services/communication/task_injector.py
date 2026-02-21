"""Inject cross-project messages as Claude Code tasks.

Writes JSON task files to ~/.claude/tasks/ so Claude Code's native
TaskList/TaskGet tools surface them to the PM agent.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)

# Priority mapping: message priority → task priority
PRIORITY_MAP = {
    "urgent": "high",
    "high": "high",
    "normal": "medium",
    "low": "low",
}


class TaskInjector:
    """Inject messages into Claude Code task list."""

    def __init__(self, tasks_dir: Optional[Path] = None):
        """Initialize with tasks directory.

        Args:
            tasks_dir: Override for ~/.claude/tasks/ (useful for testing)
        """
        self.tasks_dir = tasks_dir or (Path.home() / ".claude" / "tasks")
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def inject_message_task(
        self,
        message_id: str,
        from_project: str,
        subject: str,
        body: str,
        priority: str = "normal",
        from_agent: str = "pm",
        message_type: str = "notification",
    ) -> Path:
        """Create task file for incoming message.

        Args:
            message_id: Unique message identifier
            from_project: Absolute path of sending project
            subject: Message subject
            body: Message body
            priority: Message priority (urgent/high/normal/low)
            from_agent: Sender agent type
            message_type: Message type (task/request/notification/reply)

        Returns:
            Path to created task file
        """
        # Map priority
        task_priority = PRIORITY_MAP.get(priority, "medium")

        # Build project display name from path
        project_name = Path(from_project).name

        # Build task
        task_data = {
            "id": f"msg-{message_id}",
            "title": f"📬 Message from {project_name}: {subject}",
            "description": self._format_description(
                from_project=from_project,
                from_agent=from_agent,
                subject=subject,
                body=body,
                message_id=message_id,
                message_type=message_type,
                priority=priority,
            ),
            "status": "pending",
            "priority": task_priority,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "source": "mpm-messaging",
                "message_id": message_id,
                "from_project": from_project,
                "message_type": message_type,
                "auto_generated": True,
            },
        }

        # Write task file
        task_file = self.tasks_dir / f"msg-{message_id}.json"
        task_file.write_text(json.dumps(task_data, indent=2))

        logger.info(f"Injected task for message {message_id}: {task_file}")
        return task_file

    def task_exists(self, message_id: str) -> bool:
        """Check if task already exists for message."""
        task_file = self.tasks_dir / f"msg-{message_id}.json"
        return task_file.exists()

    def remove_task(self, message_id: str) -> bool:
        """Remove task file for message (e.g. when archived)."""
        task_file = self.tasks_dir / f"msg-{message_id}.json"
        if task_file.exists():
            task_file.unlink()
            logger.info(f"Removed task for message {message_id}")
            return True
        return False

    def cleanup_completed_tasks(self) -> int:
        """Remove completed message tasks. Returns count removed."""
        removed = 0
        for task_file in self.tasks_dir.glob("msg-*.json"):
            try:
                task_data = json.loads(task_file.read_text())
                if task_data.get("status", "").lower() in {"completed", "done"}:
                    task_file.unlink()
                    removed += 1
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error cleaning task {task_file}: {e}")

        if removed:
            logger.info(f"Cleaned up {removed} completed message tasks")
        return removed

    def list_message_tasks(self) -> list:
        """List all message-related tasks."""
        tasks = []
        for task_file in self.tasks_dir.glob("msg-*.json"):
            try:
                task_data = json.loads(task_file.read_text())
                tasks.append(task_data)
            except (json.JSONDecodeError, OSError):
                continue
        return tasks

    def _format_description(
        self,
        from_project: str,
        from_agent: str,
        subject: str,
        body: str,
        message_id: str,
        message_type: str,
        priority: str,
    ) -> str:
        """Format task description with message details."""
        type_emoji = {
            "task": "📋",
            "request": "❓",
            "notification": "📢",
            "reply": "💬",
        }.get(message_type, "📬")

        return f"""{type_emoji} Cross-project message received

From: {from_project}
Agent: {from_agent}
Type: {message_type}
Priority: {priority}
Subject: {subject}

---

{body}

---

To handle this message:
1. Read full message: claude-mpm message read {message_id}
2. Take appropriate action based on message type
3. Reply when complete: claude-mpm message reply {message_id} --body "your response"
"""
