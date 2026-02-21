"""
Cross-project message service for Claude MPM.

WHY: Enables asynchronous communication between Claude MPM instances across
different projects, allowing coordinated work without manual intervention.

DESIGN:
- Markdown files with YAML frontmatter for human readability
- File-based inbox/outbox for simplicity and reliability
- Project-scoped messages with absolute paths
- Status tracking (unread, read, archived)
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import yaml


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

    def __init__(self, project_root: Path):
        """
        Initialize message service.

        Args:
            project_root: Root directory of the current project
        """
        self.project_root = project_root
        self.inbox_dir = project_root / ".claude-mpm" / "inbox"
        self.outbox_dir = project_root / ".claude-mpm" / "outbox"
        self.archive_dir = project_root / ".claude-mpm" / "inbox" / ".archive"

        # Ensure directories exist
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

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

        # Save to outbox
        outbox_file = self.outbox_dir / f"{message_id}.md"
        outbox_file.write_text(message.to_markdown())

        # Deliver to target project's inbox
        target_project = Path(to_project)
        target_inbox = target_project / ".claude-mpm" / "inbox"
        target_inbox.mkdir(parents=True, exist_ok=True)

        inbox_message = Message(
            id=message_id,
            from_project=str(self.project_root),
            from_agent=from_agent,
            to_project=to_project,
            to_agent=to_agent,
            type=message_type,
            priority=priority,
            created_at=message.created_at,
            status="unread",
            reply_to=None,
            subject=subject,
            body=body,
            attachments=attachments or [],
            metadata=metadata or {},
        )

        inbox_file = target_inbox / f"{message_id}.md"
        inbox_file.write_text(inbox_message.to_markdown())

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
        messages = []

        # Get messages from inbox
        for msg_file in sorted(self.inbox_dir.glob("*.md")):
            try:
                message = Message.from_markdown(msg_file.read_text())

                # Apply filters
                if status and message.status != status:
                    continue
                if agent and message.to_agent != agent:
                    continue

                messages.append(message)
            except Exception as e:
                print(f"Warning: Failed to parse message {msg_file}: {e}")

        return messages

    def read_message(self, message_id: str) -> Optional[Message]:
        """
        Read a message and mark as read.

        Args:
            message_id: Message ID to read

        Returns:
            Message object or None if not found
        """
        msg_file = self.inbox_dir / f"{message_id}.md"

        if not msg_file.exists():
            return None

        message = Message.from_markdown(msg_file.read_text())

        # Mark as read
        if message.status == "unread":
            message.status = "read"
            msg_file.write_text(message.to_markdown())

        return message

    def archive_message(self, message_id: str) -> bool:
        """
        Archive a message (move to archive).

        Args:
            message_id: Message ID to archive

        Returns:
            True if archived, False if not found
        """
        msg_file = self.inbox_dir / f"{message_id}.md"

        if not msg_file.exists():
            return False

        # Move to archive
        archive_file = self.archive_dir / f"{message_id}.md"
        msg_file.rename(archive_file)

        return True

    def get_unread_count(self, agent: Optional[str] = None) -> int:
        """
        Get count of unread messages.

        Args:
            agent: Filter by target agent

        Returns:
            Number of unread messages
        """
        unread = self.list_messages(status="unread", agent=agent)
        return len(unread)

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
        return self.send_message(
            to_project=original.from_project,
            to_agent=original.from_agent,
            message_type="reply",
            subject=f"Re: {original.subject}",
            body=body,
            from_agent=from_agent,
            metadata={"reply_to": original_message_id},
        )
