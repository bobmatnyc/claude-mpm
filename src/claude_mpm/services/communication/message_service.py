"""
Cross-project message service for Claude MPM.

WHY: Enables asynchronous communication between Claude MPM instances across
different projects, allowing coordinated work without manual intervention.

DESIGN:
- SQLite database for persistent message storage
- Separate databases for inbox (received) and outbox (sent)
- Global session registry for peer discovery
- Status tracking (unread, read, archived)
"""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import yaml

from .messaging_db import MessagingDatabase


@dataclass
class Message:
    """Represents a cross-project message."""

    id: str
    from_project: str
    from_agent: str
    to_project: str
    to_agent: str
    type: str
    priority: str
    created_at: datetime
    status: str = "unread"
    reply_to: Optional[str] = None
    subject: str = ""
    body: str = ""
    attachments: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert message to markdown format with YAML frontmatter."""
        frontmatter = {
            "id": self.id,
            "from_project": self.from_project,
            "from_agent": self.from_agent,
            "to_project": self.to_project,
            "to_agent": self.to_agent,
            "type": self.type,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "reply_to": self.reply_to,
        }

        # Add metadata if present
        if self.metadata:
            frontmatter["metadata"] = self.metadata

        # Build markdown content
        content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n"

        if self.subject:
            content += f"# {self.subject}\n\n"

        content += self.body

        if self.attachments:
            content += "\n\n## Attachments\n\n"
            for attachment in self.attachments:
                content += f"- `{attachment}`\n"

        return content

    @classmethod
    def from_markdown(cls, content: str) -> "Message":
        """Parse message from markdown with YAML frontmatter."""
        # Split frontmatter and body
        parts = content.split("---\n", 2)
        if len(parts) < 3:
            raise ValueError("Invalid message format: missing frontmatter")

        frontmatter_text = parts[1]
        body_text = parts[2].strip()

        # Parse frontmatter
        frontmatter = yaml.safe_load(frontmatter_text)

        # Extract subject from first heading if present
        subject = ""
        if body_text.startswith("# "):
            lines = body_text.split("\n", 1)
            subject = lines[0][2:].strip()
            body_text = lines[1].strip() if len(lines) > 1 else ""

        # Extract attachments section if present
        attachments = []
        if "\n## Attachments\n" in body_text:
            parts = body_text.split("\n## Attachments\n", 1)
            body_text = parts[0].strip()
            attachment_lines = parts[1].strip().split("\n")
            attachments = [
                line.strip("- `").rstrip("`")
                for line in attachment_lines
                if line.strip().startswith("- `")
            ]

        return cls(
            id=frontmatter["id"],
            from_project=frontmatter["from_project"],
            from_agent=frontmatter["from_agent"],
            to_project=frontmatter["to_project"],
            to_agent=frontmatter["to_agent"],
            type=frontmatter["type"],
            priority=frontmatter["priority"],
            created_at=datetime.fromisoformat(frontmatter["created_at"]),
            status=frontmatter.get("status", "unread"),
            reply_to=frontmatter.get("reply_to"),
            subject=subject,
            body=body_text,
            attachments=attachments,
            metadata=frontmatter.get("metadata", {}),
        )


class MessageService:
    """Service for managing cross-project messages."""

    def __init__(
        self,
        project_root: Path,
        registry_path: Optional[Path] = None,
    ):
        """
        Initialize message service.

        Args:
            project_root: Root directory of the current project
            registry_path: Override for global session registry path (for testing)
        """
        self.project_root = project_root

        # Initialize databases
        self.messaging_db_path = project_root / ".claude-mpm" / "messaging.db"
        self.messaging_db = MessagingDatabase(self.messaging_db_path)

        # Global session registry (use override or default)
        self.global_registry_path = (
            registry_path or Path.home() / ".claude-mpm" / "session-registry.db"
        )
        self.global_registry = MessagingDatabase(self.global_registry_path)

        # Register current session
        self.session_id = f"session-{uuid.uuid4().hex[:8]}"
        self.global_registry.register_session(
            self.session_id, str(self.project_root), pid=os.getpid()
        )

    def send_message(
        self,
        to_project: str,
        to_agent: str,
        message_type: str,
        subject: str,
        body: str,
        priority: str = "normal",
        from_agent: str = "pm",
        attachments: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Message:
        """
        Send a message to another project.

        Args:
            to_project: Absolute path to target project
            to_agent: Target agent (pm, engineer, qa, etc.)
            message_type: Type of message (task, request, notification, reply)
            subject: Message subject/title
            body: Message body content
            priority: Message priority (low, normal, high, urgent)
            from_agent: Sending agent name
            attachments: List of file paths to attach
            metadata: Additional metadata

        Returns:
            Created message object
        """
        # Generate message ID
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        message_id = f"msg-{timestamp}-{unique_id}"

        # Create message
        message = Message(
            id=message_id,
            from_project=str(self.project_root),
            from_agent=from_agent,
            to_project=to_project,
            to_agent=to_agent,
            type=message_type,
            priority=priority,
            created_at=datetime.now(timezone.utc),
            status="sent",
            subject=subject,
            body=body,
            attachments=attachments or [],
            metadata=metadata or {},
        )

        # Save to sender's outbox database
        self.messaging_db.insert_message(
            {
                "id": message_id,
                "from_project": str(self.project_root),
                "from_agent": from_agent,
                "to_project": to_project,
                "to_agent": to_agent,
                "type": message_type,
                "priority": priority,
                "subject": subject,
                "body": body,
                "status": "sent",
                "created_at": message.created_at.isoformat(),
                "reply_to": None,
                "attachments": attachments or [],
                "metadata": metadata or {},
            }
        )

        # Deliver to target project's inbox database
        target_db_path = Path(to_project) / ".claude-mpm" / "messaging.db"
        target_db = MessagingDatabase(target_db_path)

        target_db.insert_message(
            {
                "id": message_id,
                "from_project": str(self.project_root),
                "from_agent": from_agent,
                "to_project": to_project,
                "to_agent": to_agent,
                "type": message_type,
                "priority": priority,
                "subject": subject,
                "body": body,
                "status": "unread",
                "created_at": message.created_at.isoformat(),
                "reply_to": None,
                "attachments": attachments or [],
                "metadata": metadata or {},
            }
        )

        return message

    def list_messages(
        self, status: Optional[str] = None, agent: Optional[str] = None
    ) -> List[Message]:
        """
        List messages in inbox.

        Args:
            status: Filter by status (unread, read, archived)
            agent: Filter by target agent

        Returns:
            List of messages
        """
        # Query from database
        if agent:
            db_messages = self.messaging_db.get_messages_for_agent(agent, status)
        else:
            db_messages = self.messaging_db.list_messages(status)

        # Convert to Message objects
        messages = []
        for msg_dict in db_messages:
            message = Message(
                id=msg_dict["id"],
                from_project=msg_dict["from_project"],
                from_agent=msg_dict["from_agent"],
                to_project=msg_dict["to_project"],
                to_agent=msg_dict["to_agent"],
                type=msg_dict["type"],
                priority=msg_dict["priority"],
                created_at=datetime.fromisoformat(msg_dict["created_at"]),
                status=msg_dict["status"],
                reply_to=msg_dict.get("reply_to"),
                subject=msg_dict["subject"],
                body=msg_dict["body"],
                attachments=msg_dict.get("attachments", []),
                metadata=msg_dict.get("metadata", {}),
            )
            messages.append(message)

        return messages

    def read_message(self, message_id: str) -> Optional[Message]:
        """
        Read a message and mark as read.

        Args:
            message_id: Message ID to read

        Returns:
            Message object or None if not found
        """
        # Get message from database
        msg_dict = self.messaging_db.get_message(message_id)
        if not msg_dict:
            return None

        # Mark as read
        if msg_dict["status"] == "unread":
            self.messaging_db.update_message_status(message_id, "read")

        # Convert to Message object and return
        return Message(
            id=msg_dict["id"],
            from_project=msg_dict["from_project"],
            from_agent=msg_dict["from_agent"],
            to_project=msg_dict["to_project"],
            to_agent=msg_dict["to_agent"],
            type=msg_dict["type"],
            priority=msg_dict["priority"],
            created_at=datetime.fromisoformat(msg_dict["created_at"]),
            status="read",  # Now marked as read
            reply_to=msg_dict.get("reply_to"),
            subject=msg_dict["subject"],
            body=msg_dict["body"],
            attachments=msg_dict.get("attachments", []),
            metadata=msg_dict.get("metadata", {}),
        )

    def archive_message(self, message_id: str) -> bool:
        """
        Archive a message (update status to archived).

        Args:
            message_id: Message ID to archive

        Returns:
            True if archived, False if not found
        """
        return self.messaging_db.update_message_status(message_id, "archived")

    def get_unread_count(self, agent: Optional[str] = None) -> int:
        """
        Get count of unread messages.

        Args:
            agent: Filter by target agent

        Returns:
            Number of unread messages
        """
        return self.messaging_db.get_unread_count(to_agent=agent)

    def reply_to_message(
        self,
        original_message_id: str,
        subject: str,
        body: str,
        from_agent: str = "pm",
    ) -> Optional[Message]:
        """
        Reply to a message.

        Args:
            original_message_id: ID of message being replied to
            subject: Reply subject
            body: Reply body
            from_agent: Sending agent

        Returns:
            Reply message or None if original not found
        """
        # Read original message
        original = self.read_message(original_message_id)
        if not original:
            return None

        # Send reply to original sender
        # Update original message with reply reference
        # This is optional but helpful for tracking conversation threads
        return self.send_message(
            to_project=original.from_project,
            to_agent=original.from_agent,
            message_type="reply",
            subject=f"Re: {original.subject}"
            if not subject.startswith("Re:")
            else subject,
            body=body,
            from_agent=from_agent,
            metadata={"reply_to": original_message_id},
        )

    def cleanup_old_messages(self, days_to_keep: int = 30) -> int:
        """
        Clean up old messages from the database.

        Args:
            days_to_keep: Number of days to keep messages

        Returns:
            Number of messages deleted
        """
        from datetime import timedelta

        cutoff_date = (
            datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        ).isoformat()

        with self.messaging_db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE created_at < ? AND status = 'archived'",
                (cutoff_date,),
            )
            return cursor.rowcount

    def get_high_priority_messages(self) -> List[Message]:
        """
        Get high priority unread messages.

        Returns:
            List of high priority messages
        """
        db_messages = self.messaging_db.get_high_priority_messages()

        messages = []
        for msg_dict in db_messages:
            message = Message(
                id=msg_dict["id"],
                from_project=msg_dict["from_project"],
                from_agent=msg_dict["from_agent"],
                to_project=msg_dict["to_project"],
                to_agent=msg_dict["to_agent"],
                type=msg_dict["type"],
                priority=msg_dict["priority"],
                created_at=datetime.fromisoformat(msg_dict["created_at"]),
                status=msg_dict["status"],
                reply_to=msg_dict.get("reply_to"),
                subject=msg_dict["subject"],
                body=msg_dict["body"],
                attachments=msg_dict.get("attachments", []),
                metadata=msg_dict.get("metadata", {}),
            )
            messages.append(message)

        return messages
