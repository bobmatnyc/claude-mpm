"""
SQLite database for cross-project messaging.

WHY: Provides persistent, efficient storage for messaging sessions and messages,
replacing the file-based approach with proper database management.

DESIGN:
- SQLite with WAL mode for concurrent access
- Two tables: sessions (peer discovery) and messages (communication)
- Supports both local project databases and global registry
- Efficient querying with indexes on common fields
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ...core.logging_utils import get_logger

logger = get_logger(__name__)


class MessagingDatabase:
    """SQLite database for cross-project messaging."""

    def __init__(self, db_path: Path):
        """
        Initialize database, create tables if needed.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    @contextmanager
    def get_connection(self):
        """Get a database connection with proper handling."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            # Enable WAL mode for concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _initialize_database(self) -> None:
        """Create tables and indexes if they don't exist."""
        with self.get_connection() as conn:
            # Create sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    project_path TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    pid INTEGER
                )
            """)

            # Create messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    from_project TEXT NOT NULL,
                    from_agent TEXT NOT NULL DEFAULT 'pm',
                    to_project TEXT NOT NULL,
                    to_agent TEXT NOT NULL DEFAULT 'pm',
                    message_type TEXT NOT NULL DEFAULT 'notification',
                    priority TEXT NOT NULL DEFAULT 'normal',
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'unread',
                    created_at TEXT NOT NULL,
                    read_at TEXT,
                    replied_to TEXT,
                    task_injected INTEGER NOT NULL DEFAULT 0,
                    metadata TEXT,
                    attachments TEXT
                )
            """)

            # Create indexes for efficient querying
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_to_project ON messages(to_project)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_priority ON messages(priority)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active)"
            )

    # Message operations

    def insert_message(self, message: Dict) -> str:
        """
        Insert a new message into the database.

        Args:
            message: Message dictionary with required fields

        Returns:
            Message ID
        """
        with self.get_connection() as conn:
            # Serialize JSON fields
            metadata_json = json.dumps(message.get("metadata", {}))
            attachments_json = json.dumps(message.get("attachments", []))

            conn.execute(
                """
                INSERT INTO messages (
                    id, from_project, from_agent, to_project, to_agent,
                    message_type, priority, subject, body, status,
                    created_at, replied_to, metadata, attachments
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message["id"],
                    message["from_project"],
                    message.get("from_agent", "pm"),
                    message["to_project"],
                    message.get("to_agent", "pm"),
                    message.get("type", "notification"),
                    message.get("priority", "normal"),
                    message["subject"],
                    message["body"],
                    message.get("status", "unread"),
                    message.get("created_at", datetime.now(timezone.utc).isoformat()),
                    message.get("reply_to"),
                    metadata_json,
                    attachments_json,
                ),
            )

        logger.debug(f"Inserted message {message['id']}")
        return message["id"]

    def get_message(self, message_id: str) -> Optional[Dict]:
        """
        Get a message by ID.

        Args:
            message_id: Message ID

        Returns:
            Message dict or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_message_dict(row)
            return None

    def list_messages(
        self, status: Optional[str] = None, limit: int = 50
    ) -> List[Dict]:
        """
        List messages with optional filtering.

        Args:
            status: Filter by status (unread, read, archived)
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        with self.get_connection() as conn:
            query = "SELECT * FROM messages"
            params = []

            if status:
                query += " WHERE status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            return [self._row_to_message_dict(row) for row in cursor.fetchall()]

    def update_message_status(self, message_id: str, status: str) -> bool:
        """
        Update message status.

        Args:
            message_id: Message ID
            status: New status (read, archived, etc.)

        Returns:
            True if updated, False if not found
        """
        with self.get_connection() as conn:
            # Update read_at if marking as read
            if status == "read":
                cursor = conn.execute(
                    """
                    UPDATE messages
                    SET status = ?, read_at = ?
                    WHERE id = ?
                    """,
                    (status, datetime.now(timezone.utc).isoformat(), message_id),
                )
            else:
                cursor = conn.execute(
                    "UPDATE messages SET status = ? WHERE id = ?",
                    (status, message_id),
                )

            return cursor.rowcount > 0

    def mark_task_injected(self, message_id: str) -> bool:
        """
        Mark a message as having its task injected.

        Args:
            message_id: Message ID

        Returns:
            True if updated, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE messages SET task_injected = 1 WHERE id = ?",
                (message_id,),
            )
            return cursor.rowcount > 0

    def get_unread_count(self, to_agent: Optional[str] = None) -> int:
        """
        Get count of unread messages.

        Args:
            to_agent: Optional filter by target agent

        Returns:
            Number of unread messages
        """
        with self.get_connection() as conn:
            if to_agent:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE status = 'unread' AND to_agent = ?",
                    (to_agent,),
                )
            else:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE status = 'unread'"
                )

            return cursor.fetchone()[0]

    # Session operations

    def register_session(
        self, session_id: str, project_path: str, pid: Optional[int] = None
    ) -> None:
        """
        Register a new session or update existing one.

        Args:
            session_id: Unique session identifier
            project_path: Absolute path to project
            pid: Process ID (optional)
        """
        project_name = Path(project_path).name
        now = datetime.now(timezone.utc).isoformat()

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    session_id, project_path, project_name,
                    started_at, last_active, status, pid
                ) VALUES (?, ?, ?, ?, ?, 'active', ?)
                """,
                (
                    session_id,
                    project_path,
                    project_name,
                    now,
                    now,
                    pid or os.getpid(),
                ),
            )

        logger.debug(f"Registered session {session_id} for {project_name}")

    def update_heartbeat(self, session_id: str) -> None:
        """
        Update session heartbeat timestamp.

        Args:
            session_id: Session ID to update
        """
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                (datetime.now(timezone.utc).isoformat(), session_id),
            )

    def deregister_session(self, session_id: str) -> None:
        """
        Mark session as inactive.

        Args:
            session_id: Session ID to deregister
        """
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET status = 'inactive' WHERE session_id = ?",
                (session_id,),
            )
        logger.debug(f"Deregistered session {session_id}")

    def list_active_sessions(self) -> List[Dict]:
        """
        List all active sessions.

        Returns:
            List of session dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sessions
                WHERE status = 'active'
                ORDER BY last_active DESC
                """
            )
            return [
                {
                    "session_id": row["session_id"],
                    "project_path": row["project_path"],
                    "project_name": row["project_name"],
                    "started_at": row["started_at"],
                    "last_active": row["last_active"],
                    "status": row["status"],
                    "pid": row["pid"],
                }
                for row in cursor.fetchall()
            ]

    def cleanup_stale_sessions(self, timeout_minutes: int = 60) -> int:
        """
        Mark stale sessions as inactive.

        Args:
            timeout_minutes: Minutes of inactivity before marking stale

        Returns:
            Number of sessions marked as stale
        """
        from datetime import timedelta

        cutoff_time = (
            datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        ).isoformat()

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE sessions
                SET status = 'stale'
                WHERE status = 'active' AND last_active < ?
                """,
                (cutoff_time,),
            )
            count = cursor.rowcount

        if count > 0:
            logger.info(f"Marked {count} sessions as stale")

        return count

    # Helper methods

    def _row_to_message_dict(self, row: sqlite3.Row) -> Dict:
        """Convert database row to message dictionary."""
        return {
            "id": row["id"],
            "from_project": row["from_project"],
            "from_agent": row["from_agent"],
            "to_project": row["to_project"],
            "to_agent": row["to_agent"],
            "type": row["message_type"],
            "priority": row["priority"],
            "subject": row["subject"],
            "body": row["body"],
            "status": row["status"],
            "created_at": row["created_at"],
            "read_at": row["read_at"],
            "reply_to": row["replied_to"],
            "task_injected": bool(row["task_injected"]),
            "metadata": json.loads(row["metadata"] or "{}"),
            "attachments": json.loads(row["attachments"] or "[]"),
        }

    def get_messages_for_agent(
        self, to_agent: str, status: Optional[str] = None, limit: int = 50
    ) -> List[Dict]:
        """
        Get messages for a specific agent.

        Args:
            to_agent: Target agent name
            status: Optional status filter
            limit: Maximum number of messages

        Returns:
            List of message dictionaries
        """
        with self.get_connection() as conn:
            if status:
                cursor = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE to_agent = ? AND status = ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (to_agent, status, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE to_agent = ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (to_agent, limit),
                )

            return [self._row_to_message_dict(row) for row in cursor.fetchall()]

    def get_high_priority_messages(
        self, priorities: Optional[List[str]] = None, limit: int = 50
    ) -> List[Dict]:
        """
        Get high priority messages.

        Args:
            priorities: List of priority levels to include
            limit: Maximum number of messages

        Returns:
            List of high priority messages
        """
        if not priorities:
            priorities = ["high", "urgent"]

        with self.get_connection() as conn:
            placeholders = ",".join("?" * len(priorities))
            cursor = conn.execute(
                f"""
                SELECT * FROM messages
                WHERE priority IN ({placeholders}) AND status = 'unread'
                ORDER BY
                    CASE priority
                        WHEN 'urgent' THEN 0
                        WHEN 'high' THEN 1
                        ELSE 2
                    END,
                    created_at DESC
                LIMIT ?
                """,  # nosec B608
                (*priorities, limit),
            )

            return [self._row_to_message_dict(row) for row in cursor.fetchall()]
