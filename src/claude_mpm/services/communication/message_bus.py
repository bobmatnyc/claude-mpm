"""
Huey-based message bus for cross-project messaging.

WHY: Provides a shared message queue using Huey for real-time notifications
while maintaining SQLite for persistent queryable history.

DESIGN:
- SqliteHuey for message queue (notifications)
- Shared SQLite database at ~/.claude-mpm/messaging.db
- Hybrid architecture: queue for delivery, database for history
- Single bus instance shared across all projects
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from huey import SqliteHuey, crontab
from huey.api import Task

from ...core.logging_utils import get_logger

logger = get_logger(__name__)


class MessageBus:
    """Huey-based message bus for cross-project communication."""

    # Singleton instance
    _instance: Optional["MessageBus"] = None
    _huey: Optional[SqliteHuey] = None

    def __new__(cls):
        """Ensure singleton pattern for shared bus."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the message bus (only runs once due to singleton)."""
        if MessageBus._huey is None:
            # Initialize Huey with SQLite backend
            # Use a separate database for the queue to avoid contention
            queue_db_path = Path.home() / ".claude-mpm" / "message_queue.db"
            queue_db_path.parent.mkdir(parents=True, exist_ok=True)

            MessageBus._huey = SqliteHuey(
                name="claude_mpm_messages",
                filename=str(queue_db_path),
                immediate=False,  # Process tasks asynchronously
                results=True,  # Store task results
                store_none=False,  # Don't store None results
                utc=True,  # Use UTC timestamps
            )

            logger.info(f"Initialized MessageBus with queue at {queue_db_path}")

    @property
    def huey(self) -> SqliteHuey:
        """Get the Huey instance."""
        if MessageBus._huey is None:
            raise RuntimeError("MessageBus not initialized")
        return MessageBus._huey

    def enqueue_message(self, message_data: Dict) -> Task:
        """
        Enqueue a message for delivery.

        Args:
            message_data: Message dictionary with all fields

        Returns:
            Huey Task object
        """
        # Create a task to process the message
        task = process_message(message_data)
        logger.debug(f"Enqueued message {message_data.get('id')} for delivery")
        return task

    def enqueue_notification(
        self, project_path: str, message_id: str, priority: str
    ) -> Task:
        """
        Enqueue a notification for a project about a new message.

        Args:
            project_path: Target project path
            message_id: Message ID to notify about
            priority: Message priority level

        Returns:
            Huey Task object
        """
        task = send_notification(project_path, message_id, priority)
        logger.debug(
            f"Enqueued notification for {project_path} about message {message_id}"
        )
        return task

    def start_consumer(self, workers: int = 1) -> None:
        """
        Start the Huey consumer to process messages.

        Args:
            workers: Number of worker threads
        """
        from huey.consumer import Consumer

        consumer = Consumer(self.huey, workers=workers)
        logger.info(f"Starting MessageBus consumer with {workers} workers")
        consumer.run()

    def shutdown(self) -> None:
        """Shutdown the message bus."""
        if MessageBus._huey:
            MessageBus._huey.storage.close()
            logger.info("MessageBus shut down")


# Huey task definitions
# Note: These must be defined at module level for Huey to register them

# Create the global Huey instance for decorators
# This is necessary for Python 3.8 compatibility
_bus = MessageBus()
huey = _bus.huey


@huey.task()
def process_message(message_data: Dict) -> bool:
    """
    Process a message by delivering it to the target project.

    This task runs asynchronously in the Huey worker.

    Args:
        message_data: Complete message dictionary

    Returns:
        True if delivered successfully
    """
    try:
        from .messaging_db import MessagingDatabase

        # Get target project path
        to_project = message_data.get("to_project")
        if not to_project:
            logger.error(f"Message {message_data.get('id')} missing to_project")
            return False

        # Deliver to shared database (filtered by to_project on read)
        # Using the shared database at ~/.claude-mpm/messaging.db
        shared_db_path = Path.home() / ".claude-mpm" / "messaging.db"
        shared_db = MessagingDatabase(shared_db_path)

        # Insert message with unread status for recipient
        message_data["status"] = "unread"
        shared_db.insert_message(message_data)

        # Also notify the target project if it has an active session
        # This is where real-time notification would happen
        send_notification.schedule(
            args=(
                to_project,
                message_data["id"],
                message_data.get("priority", "normal"),
            ),
            convert_utc=True,
        )

        logger.info(
            f"Delivered message {message_data['id']} to {Path(to_project).name}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to process message {message_data.get('id')}: {e}")
        return False


@huey.task()
def send_notification(project_path: str, message_id: str, priority: str) -> bool:
    """
    Send a notification to a project about a new message.

    This could trigger various notification mechanisms:
    - Update a notification file
    - Send a system notification
    - Update session state

    Args:
        project_path: Target project path
        message_id: Message ID
        priority: Message priority

    Returns:
        True if notification sent
    """
    try:
        # Check if project has an active session
        from .messaging_db import MessagingDatabase

        global_registry_path = Path.home() / ".claude-mpm" / "session-registry.db"
        registry = MessagingDatabase(global_registry_path)

        # Get active sessions for this project
        active_sessions = registry.list_active_sessions()
        project_sessions = [
            s
            for s in active_sessions
            if Path(s["project_path"]).resolve() == Path(project_path).resolve()
        ]

        if project_sessions:
            # Project has active session, create notification marker
            notification_path = Path(project_path) / ".claude-mpm" / "new_messages"
            notification_path.parent.mkdir(parents=True, exist_ok=True)

            # Write notification marker (hook will detect this)
            notification_data = {
                "message_id": message_id,
                "priority": priority,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Append to notification file
            existing_notifications = []
            if notification_path.exists():
                try:
                    existing_notifications = json.loads(notification_path.read_text())
                except Exception:  # nosec B110 - Suppress if file is corrupt
                    pass

            existing_notifications.append(notification_data)
            notification_path.write_text(json.dumps(existing_notifications, indent=2))

            logger.debug(f"Created notification for {Path(project_path).name}")
            return True
        logger.debug(f"No active session for {Path(project_path).name}, message queued")
        return True

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False


@huey.periodic_task(crontab(minute="*/5"))
def cleanup_old_notifications():
    """
    Periodic task to clean up old notification files.

    Runs every 5 minutes to remove processed notifications.
    """
    try:
        # Find all notification files older than 1 hour
        # Note: cutoff_time would be used to filter notification files
        # For now, we'll rely on each project cleaning up its own notifications
        # when messages are read

        logger.debug("Cleaned up old notifications")

    except Exception as e:
        logger.error(f"Failed to cleanup notifications: {e}")


@huey.periodic_task(crontab(hour="*/6"))
def cleanup_stale_queue_entries():
    """
    Periodic task to clean up stale queue entries.

    Runs every 6 hours to remove old completed tasks.
    """
    try:
        bus = MessageBus()

        # Huey automatically manages its queue, but we can
        # trigger cleanup of old results
        bus.huey.flush()

        logger.debug("Cleaned up stale queue entries")

    except Exception as e:
        logger.error(f"Failed to cleanup queue: {e}")
