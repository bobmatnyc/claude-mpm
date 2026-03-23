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
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ...core.logging_utils import get_logger
from .messaging_db import MessagingDatabase

logger = get_logger(__name__)


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
    reply_to: str | None = None
    subject: str = ""
    body: str = ""
    attachments: list[str] = field(default_factory=list)
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
        registry_path: Path | None = None,
        messaging_db_path: Path | None = None,
    ):
        """
        Initialize message service.

        Args:
            project_root: Root directory of the current project
            registry_path: Override for global session registry path (for testing)
            messaging_db_path: Override for shared messaging database path (for testing)
        """
        # Normalize project root with FS-canonical case (see _canonical_path docstring)
        self.project_root = Path(self._canonical_path(str(project_root)))

        # Use SHARED database for all projects (not per-project)
        # This is the key change for the Huey migration
        self.messaging_db_path = (
            messaging_db_path or Path.home() / ".claude-mpm" / "messaging.db"
        )
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

        # Initialize message bus for notifications
        from .message_bus import MessageBus

        self.message_bus = MessageBus()

    @staticmethod
    def _canonical_path(path: str) -> str:
        """Return the filesystem-canonical absolute path, including correct case.

        WHY: On macOS (case-insensitive, case-preserving HFS+/APFS), Path.resolve()
        preserves the caller's casing (e.g. '/apex') rather than the real directory
        name (e.g. '/APEX'), while os.getcwd() from inside that directory returns
        the real name.  This causes exact-match SQL queries to miss messages because
        the stored path and the queried path differ only in case.

        FIX: Walk each component through os.scandir() so we always get the name the
        filesystem actually uses, regardless of what the caller typed.

        Falls back gracefully to Path.resolve() if any component can't be read
        (e.g. symlink target doesn't exist, permission error) or if canonicalization
        produces unexpected results.
        """
        original_path = path
        resolved = Path(path).expanduser().resolve()
        parts = resolved.parts  # e.g. ('/', 'Users', 'masa', 'Duetto', 'repos', 'apex')

        if not parts:
            logger.debug(
                f"_canonical_path: Empty parts for path '{original_path}', using resolved: {resolved}"
            )
            return str(resolved)

        # Extract expected project name from original path for validation
        original_basename = Path(original_path).name
        logger.debug(
            f"_canonical_path: Processing '{original_path}' -> expected basename: '{original_basename}'"
        )

        canonical = Path(parts[0])  # start at root '/'
        for part in parts[1:]:
            try:
                # Find the real-cased entry in the parent directory
                found = False
                for entry in os.scandir(canonical):
                    if entry.name.lower() == part.lower():
                        canonical = canonical / entry.name
                        found = True
                        logger.debug(
                            f"_canonical_path: Found real-cased '{entry.name}' for '{part}'"
                        )
                        break

                if not found:
                    # Component not found on disk — append as-is
                    canonical = canonical / part
                    logger.debug(
                        f"_canonical_path: Component '{part}' not found on disk, appending as-is"
                    )

            except OSError as e:
                # Can't read directory — fall back to user-supplied component
                canonical = canonical / part
                logger.debug(
                    f"_canonical_path: OSError reading directory for '{part}': {e}, falling back to original component"
                )

        canonical_str = str(canonical)
        canonical_basename = Path(canonical_str).name

        # Validate that canonical path points to expected project
        if (
            original_basename
            and canonical_basename.lower() != original_basename.lower()
        ):
            logger.warning(
                f"_canonical_path: Canonical path basename '{canonical_basename}' doesn't match "
                f"expected '{original_basename}' for path '{original_path}'. "
                f"This may indicate path resolution issues."
            )

            # Fallback to original resolved path if canonicalization produces unexpected results
            if resolved.exists():
                logger.info(
                    f"_canonical_path: Using fallback resolved path: {resolved}"
                )
                return str(resolved)
            logger.warning(
                "_canonical_path: Fallback path doesn't exist, using canonical result anyway"
            )

        logger.debug(
            f"_canonical_path: Final result: '{original_path}' -> '{canonical_str}'"
        )
        return canonical_str

    def send_message(
        self,
        to_project: str,
        to_agent: str,
        message_type: str,
        subject: str,
        body: str,
        priority: str = "normal",
        from_agent: str = "pm",
        attachments: list[str] | None = None,
        metadata: dict | None = None,
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
        # Normalize to_project path using FS-canonical case resolution.
        # Path.resolve() preserves the caller's casing on macOS (case-insensitive FS),
        # but os.getcwd() returns the real FS name.  _canonical_path() reconciles both.
        to_project_normalized = self._canonical_path(to_project)

        # Generate message ID
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        message_id = f"msg-{timestamp}-{unique_id}"

        # Create message (using normalized path)
        message = Message(
            id=message_id,
            from_project=str(self.project_root),
            from_agent=from_agent,
            to_project=to_project_normalized,
            to_agent=to_agent,
            type=message_type,
            priority=priority,
            created_at=datetime.now(UTC),
            status="sent",
            subject=subject,
            body=body,
            attachments=attachments or [],
            metadata=metadata or {},
        )

        # Check if sending to self (same project)
        is_self_message = Path(to_project_normalized).resolve() == self.project_root

        # Prepare message data for database
        message_dict = {
            "id": message_id,
            "from_project": str(self.project_root),
            "from_agent": from_agent,
            "to_project": to_project_normalized,
            "to_agent": to_agent,
            "type": message_type,
            "priority": priority,
            "subject": subject,
            "body": body,
            "status": "sent" if not is_self_message else "unread",
            "created_at": message.created_at.isoformat(),
            "reply_to": None,
            "attachments": attachments or [],
            "metadata": metadata or {},
        }

        # Insert message to shared database
        # For shared database model: store one copy with recipient's status
        # The message is queryable by to_project (recipient queries their inbox)
        if not is_self_message:
            message_dict["status"] = "unread"  # Recipient's status

        # Insert to shared database
        self.messaging_db.insert_message(message_dict)

        # Enqueue notification for recipient (non-blocking, optional)
        if not is_self_message:
            try:
                self.message_bus.enqueue_notification(
                    to_project_normalized, message_id, priority
                )
            except Exception as e:
                # Notification failure should not prevent message delivery
                logger.warning(f"Failed to enqueue notification: {e}")

        return message

    def list_messages(
        self, status: str | None = None, agent: str | None = None
    ) -> list[Message]:
        """
        List messages in inbox.

        Args:
            status: Filter by status (unread, read, archived)
            agent: Filter by target agent

        Returns:
            List of messages
        """
        # Query from shared database, filtering by current project
        current_project = str(self.project_root)

        if agent:
            db_messages = self.messaging_db.get_messages_for_project_and_agent(
                current_project, agent, status
            )
        else:
            db_messages = self.messaging_db.get_messages_for_project(
                current_project, status
            )

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

    def read_message(self, message_id: str) -> Message | None:
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

    def get_unread_count(self, agent: str | None = None) -> int:
        """
        Get count of unread messages.

        Args:
            agent: Filter by target agent

        Returns:
            Number of unread messages
        """
        # Filter by current project
        return self.messaging_db.get_unread_count_for_project(
            str(self.project_root), to_agent=agent
        )

    def reply_to_message(
        self,
        original_message_id: str,
        subject: str,
        body: str,
        from_agent: str = "pm",
    ) -> Message | None:
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
        # Determine reply subject
        if subject and subject.startswith("Re:"):
            # Use provided subject if it already has "Re:" prefix
            reply_subject = subject
        elif subject:
            # Use provided subject with "Re:" prefix
            reply_subject = f"Re: {subject}"
        # Use original subject with "Re:" prefix if it doesn't already have it
        elif original.subject and original.subject.startswith("Re:"):
            reply_subject = original.subject
        else:
            reply_subject = f"Re: {original.subject or 'Your message'}"

        return self.send_message(
            to_project=original.from_project,
            to_agent=original.from_agent,
            message_type="reply",
            subject=reply_subject,
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

        cutoff_date = (datetime.now(UTC) - timedelta(days=days_to_keep)).isoformat()

        with self.messaging_db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE created_at < ? AND status = 'archived'",
                (cutoff_date,),
            )
            return cursor.rowcount

    def get_high_priority_messages(self) -> list[Message]:
        """
        Get high priority unread messages.

        Returns:
            List of high priority messages
        """
        # Filter by current project
        db_messages = self.messaging_db.get_high_priority_messages_for_project(
            str(self.project_root)
        )

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
