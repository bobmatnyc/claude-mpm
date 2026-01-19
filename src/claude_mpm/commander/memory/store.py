"""Conversation storage with SQLite and vector support.

This module provides CRUD operations for conversations with vector embeddings
for semantic search. Uses SQLite with optional sqlite-vec extension.
"""

import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.project import ThreadMessage

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


@dataclass
class ConversationMessage:
    """Single message in a conversation.

    Attributes:
        role: Message sender role ('user', 'assistant', 'system', 'tool')
        content: Message content
        timestamp: Message creation timestamp
        token_count: Approximate token count (content length / 4)
        entities: Extracted entities (files, functions, errors)
        metadata: Additional metadata (tool name, error type, etc.)

    Example:
        >>> msg = ConversationMessage(
        ...     role="user",
        ...     content="Fix the login bug in auth.py",
        ...     entities=[{"type": "file", "value": "auth.py"}]
        ... )
    """

    role: str
    content: str
    timestamp: datetime = field(default_factory=_utc_now)
    token_count: int = field(default=0)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Calculate token count if not provided."""
        if self.token_count == 0:
            # Rough approximation: 1 token ≈ 4 characters
            self.token_count = len(self.content) // 4

    @classmethod
    def from_thread_message(cls, msg: ThreadMessage) -> "ConversationMessage":
        """Convert ThreadMessage to ConversationMessage.

        Args:
            msg: ThreadMessage from project thread

        Returns:
            ConversationMessage with extracted data
        """
        return cls(
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
            entities=[],
            metadata={
                "thread_message_id": msg.id,
                "session_id": msg.session_id,
                "event_id": msg.event_id,
            },
        )


@dataclass
class Conversation:
    """Complete conversation thread.

    Attributes:
        id: Unique conversation identifier (UUID)
        project_id: Parent project ID
        instance_name: Instance name (e.g., "claude-code-1")
        session_id: Session ID from ToolSession
        messages: List of conversation messages
        summary: Optional compressed summary
        embedding: Optional vector embedding for semantic search
        created_at: Conversation creation timestamp
        updated_at: Last update timestamp
        metadata: Additional metadata (framework, version, etc.)

    Example:
        >>> conversation = Conversation(
        ...     id="conv-abc123",
        ...     project_id="proj-xyz",
        ...     instance_name="claude-code-1",
        ...     session_id="sess-123",
        ...     messages=[msg1, msg2, msg3]
        ... )
    """

    id: str
    project_id: str
    instance_name: str
    session_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    summary: Optional[str] = None
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Calculate total token count across all messages."""
        return sum(msg.token_count for msg in self.messages)

    @property
    def message_count(self) -> int:
        """Return number of messages in conversation."""
        return len(self.messages)

    def get_full_text(self) -> str:
        """Get full conversation as text.

        Returns:
            Formatted conversation text with role prefixes
        """
        lines = []
        for msg in self.messages:
            lines.append(f"{msg.role.upper()}: {msg.content}")
        return "\n\n".join(lines)


class ConversationStore:
    """Persists conversations to SQLite with vector support.

    Provides CRUD operations and vector search capabilities using
    SQLite with optional sqlite-vec extension.

    Attributes:
        db_path: Path to SQLite database file
        enable_vector: Whether to enable vector extension

    Example:
        >>> store = ConversationStore()
        >>> await store.save(conversation)
        >>> results = await store.search("login bug", limit=5)
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        enable_vector: bool = True,
    ):
        """Initialize conversation store.

        Args:
            db_path: Path to database file (default: ~/.claude-mpm/commander/conversations.db)
            enable_vector: Enable vector extension for semantic search
        """
        if db_path is None:
            db_path = Path("~/.claude-mpm/commander/conversations.db").expanduser()

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.enable_vector = enable_vector

        # Initialize schema
        asyncio.create_task(self._init_schema())

        logger.info(
            "ConversationStore initialized at %s (vector: %s)",
            self.db_path,
            enable_vector,
        )

    async def _init_schema(self) -> None:
        """Initialize database schema.

        Creates tables for conversations and messages if they don't exist.
        Optionally loads sqlite-vec extension for vector operations.
        """

        def _create_schema(conn: sqlite3.Connection) -> None:
            """Create schema in sync context."""
            # Try to load sqlite-vec extension
            if self.enable_vector:
                try:
                    conn.enable_load_extension(True)
                    # Try common locations for sqlite-vec
                    # Users need to install: pip install sqlite-vec
                    try:
                        conn.load_extension("vec0")
                        logger.info("Loaded sqlite-vec extension")
                    except sqlite3.OperationalError:
                        logger.warning(
                            "sqlite-vec extension not found. "
                            "Install with: pip install sqlite-vec. "
                            "Falling back to non-vector search."
                        )
                        self.enable_vector = False
                except Exception as e:
                    logger.warning("Cannot load extensions: %s", e)
                    self.enable_vector = False

            # Create conversations table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    instance_name TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT,
                    UNIQUE(session_id)
                )
            """
            )

            # Create messages table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    entities TEXT,
                    metadata TEXT,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                )
            """
            )

            # Create embeddings table (if vector enabled)
            if self.enable_vector:
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS conversation_embeddings
                    USING vec0(
                        conversation_id TEXT PRIMARY KEY,
                        embedding FLOAT[384]
                    )
                """
                )

            # Create indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_project "
                "ON conversations(project_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_session "
                "ON conversations(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation "
                "ON messages(conversation_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_updated "
                "ON conversations(updated_at)"
            )

            conn.commit()

        # Run in executor to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._execute_sync(_create_schema),
        )

    def _execute_sync(self, func: Any) -> Any:
        """Execute synchronous database operation.

        Args:
            func: Function that takes connection and executes queries

        Returns:
            Result from func
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            return func(conn)
        finally:
            conn.close()

    async def save(self, conversation: Conversation) -> None:
        """Save conversation to database.

        Updates existing conversation or inserts new one.

        Args:
            conversation: Conversation to persist

        Example:
            >>> await store.save(conversation)
        """

        def _save(conn: sqlite3.Connection) -> None:
            """Save in sync context."""
            # Upsert conversation
            conn.execute(
                """
                INSERT OR REPLACE INTO conversations
                (id, project_id, instance_name, session_id, summary,
                 created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    conversation.id,
                    conversation.project_id,
                    conversation.instance_name,
                    conversation.session_id,
                    conversation.summary,
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                    json.dumps(conversation.metadata),
                ),
            )

            # Delete old messages
            conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation.id,),
            )

            # Insert messages
            for msg in conversation.messages:
                conn.execute(
                    """
                    INSERT INTO messages
                    (conversation_id, role, content, timestamp,
                     token_count, entities, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        conversation.id,
                        msg.role,
                        msg.content,
                        msg.timestamp.isoformat(),
                        msg.token_count,
                        json.dumps(msg.entities),
                        json.dumps(msg.metadata),
                    ),
                )

            # Save embedding if available
            if self.enable_vector and conversation.embedding:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO conversation_embeddings
                    (conversation_id, embedding)
                    VALUES (?, ?)
                """,
                    (conversation.id, json.dumps(conversation.embedding)),
                )

            conn.commit()

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._execute_sync(_save)
        )

        logger.debug(
            "Saved conversation %s (%d messages)",
            conversation.id,
            len(conversation.messages),
        )

    async def load(self, conversation_id: str) -> Optional[Conversation]:
        """Load conversation by ID.

        Args:
            conversation_id: Conversation ID to load

        Returns:
            Conversation if found, None otherwise

        Example:
            >>> conv = await store.load("conv-abc123")
        """

        def _load(conn: sqlite3.Connection) -> Optional[Conversation]:
            """Load in sync context."""
            # Load conversation
            cursor = conn.execute(
                """
                SELECT id, project_id, instance_name, session_id, summary,
                       created_at, updated_at, metadata
                FROM conversations
                WHERE id = ?
            """,
                (conversation_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            # Load messages
            messages_cursor = conn.execute(
                """
                SELECT role, content, timestamp, token_count, entities, metadata
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
            """,
                (conversation_id,),
            )

            messages = []
            for msg_row in messages_cursor.fetchall():
                messages.append(
                    ConversationMessage(
                        role=msg_row[0],
                        content=msg_row[1],
                        timestamp=datetime.fromisoformat(msg_row[2]),
                        token_count=msg_row[3],
                        entities=json.loads(msg_row[4]) if msg_row[4] else [],
                        metadata=json.loads(msg_row[5]) if msg_row[5] else {},
                    )
                )

            # Load embedding if available
            embedding = None
            if self.enable_vector:
                emb_cursor = conn.execute(
                    "SELECT embedding FROM conversation_embeddings WHERE conversation_id = ?",
                    (conversation_id,),
                )
                emb_row = emb_cursor.fetchone()
                if emb_row:
                    embedding = json.loads(emb_row[0])

            return Conversation(
                id=row[0],
                project_id=row[1],
                instance_name=row[2],
                session_id=row[3],
                summary=row[4],
                created_at=datetime.fromisoformat(row[5]),
                updated_at=datetime.fromisoformat(row[6]),
                metadata=json.loads(row[7]) if row[7] else {},
                messages=messages,
                embedding=embedding,
            )

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._execute_sync(_load)
        )

    async def list_by_project(
        self,
        project_id: str,
        limit: Optional[int] = None,
    ) -> List[Conversation]:
        """List conversations for a project.

        Args:
            project_id: Project ID to filter by
            limit: Maximum number of results

        Returns:
            List of conversations ordered by updated_at descending

        Example:
            >>> conversations = await store.list_by_project("proj-xyz", limit=10)
        """

        def _list(conn: sqlite3.Connection) -> List[Conversation]:
            """List in sync context."""
            query = """
                SELECT id FROM conversations
                WHERE project_id = ?
                ORDER BY updated_at DESC
            """
            if limit:
                query += f" LIMIT {limit}"

            cursor = conn.execute(query, (project_id,))
            conversation_ids = [row[0] for row in cursor.fetchall()]

            # Load full conversations
            conversations = []
            for conv_id in conversation_ids:
                conv = self._execute_sync(lambda c: self._load_conversation(c, conv_id))
                if conv:
                    conversations.append(conv)

            return conversations

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._execute_sync(_list)
        )

    def _load_conversation(
        self, conn: sqlite3.Connection, conversation_id: str
    ) -> Optional[Conversation]:
        """Load conversation in sync context (helper for list operations)."""
        cursor = conn.execute(
            """
            SELECT id, project_id, instance_name, session_id, summary,
                   created_at, updated_at, metadata
            FROM conversations
            WHERE id = ?
        """,
            (conversation_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        # Load messages
        messages_cursor = conn.execute(
            """
            SELECT role, content, timestamp, token_count, entities, metadata
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
        """,
            (conversation_id,),
        )

        messages = []
        for msg_row in messages_cursor.fetchall():
            messages.append(
                ConversationMessage(
                    role=msg_row[0],
                    content=msg_row[1],
                    timestamp=datetime.fromisoformat(msg_row[2]),
                    token_count=msg_row[3],
                    entities=json.loads(msg_row[4]) if msg_row[4] else [],
                    metadata=json.loads(msg_row[5]) if msg_row[5] else {},
                )
            )

        return Conversation(
            id=row[0],
            project_id=row[1],
            instance_name=row[2],
            session_id=row[3],
            summary=row[4],
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
            metadata=json.loads(row[7]) if row[7] else {},
            messages=messages,
        )

    async def search_by_text(
        self,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Conversation]:
        """Search conversations by text (fallback when vectors unavailable).

        Uses SQLite FTS5 full-text search on conversation content.

        Args:
            query: Search query
            project_id: Optional project ID filter
            limit: Maximum results

        Returns:
            List of matching conversations

        Example:
            >>> results = await store.search_by_text("login bug fix")
        """

        def _search(conn: sqlite3.Connection) -> List[str]:
            """Search in sync context."""
            # Simple LIKE search (can be improved with FTS5)
            if project_id:
                cursor = conn.execute(
                    """
                    SELECT DISTINCT c.id
                    FROM conversations c
                    JOIN messages m ON c.id = m.conversation_id
                    WHERE c.project_id = ? AND (
                        c.summary LIKE ? OR m.content LIKE ?
                    )
                    ORDER BY c.updated_at DESC
                    LIMIT ?
                """,
                    (project_id, f"%{query}%", f"%{query}%", limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT DISTINCT c.id
                    FROM conversations c
                    JOIN messages m ON c.id = m.conversation_id
                    WHERE c.summary LIKE ? OR m.content LIKE ?
                    ORDER BY c.updated_at DESC
                    LIMIT ?
                """,
                    (f"%{query}%", f"%{query}%", limit),
                )

            return [row[0] for row in cursor.fetchall()]

        conversation_ids = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._execute_sync(_search)
        )

        # Load full conversations
        conversations = []
        for conv_id in conversation_ids:
            conv = await self.load(conv_id)
            if conv:
                conversations.append(conv)

        return conversations

    async def delete(self, conversation_id: str) -> None:
        """Delete conversation and all messages.

        Args:
            conversation_id: Conversation ID to delete

        Example:
            >>> await store.delete("conv-abc123")
        """

        def _delete(conn: sqlite3.Connection) -> None:
            """Delete in sync context."""
            conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?", (conversation_id,)
            )
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            if self.enable_vector:
                conn.execute(
                    "DELETE FROM conversation_embeddings WHERE conversation_id = ?",
                    (conversation_id,),
                )
            conn.commit()

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._execute_sync(_delete)
        )

        logger.debug("Deleted conversation %s", conversation_id)
