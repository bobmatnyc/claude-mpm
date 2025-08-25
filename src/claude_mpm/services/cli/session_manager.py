"""Session management service for CLI commands.

WHY: This service extracts session lifecycle management from run.py to improve
separation of concerns, testability, and reusability across CLI commands. It
handles session creation, loading, validation, and persistence.

DESIGN DECISIONS:
- Interface-based design for dependency injection
- Single responsibility: session lifecycle management
- Supports multiple session contexts (default, orchestration, etc.)
- Automatic session cleanup and archiving
- Thread-safe session operations
- Non-blocking validation with structured warnings
"""

import gzip
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.logger import get_logger


# Interface Definition
class ISessionManager(ABC):
    """Interface for session management service."""

    @abstractmethod
    def create_session(
        self, context: str = "default", options: Optional[Dict[str, Any]] = None
    ) -> "SessionInfo":
        """Create a new session with options.

        Args:
            context: Session context (e.g., 'default', 'orchestration')
            options: Optional session configuration

        Returns:
            SessionInfo object with session details
        """

    @abstractmethod
    def load_session(self, session_id: str) -> Optional["SessionInfo"]:
        """Load an existing session by ID.

        Args:
            session_id: Session UUID

        Returns:
            SessionInfo if found, None otherwise
        """

    @abstractmethod
    def save_session(self, session_info: "SessionInfo") -> bool:
        """Persist session state to storage.

        Args:
            session_info: Session to save

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata.

        Args:
            session_id: Session UUID

        Returns:
            Session metadata dictionary or None
        """

    @abstractmethod
    def validate_session(self, session_id: str) -> "SessionValidation":
        """Validate session consistency and health.

        Args:
            session_id: Session UUID

        Returns:
            SessionValidation with results
        """

    @abstractmethod
    def get_recent_sessions(
        self, limit: int = 10, context: Optional[str] = None
    ) -> List["SessionInfo"]:
        """Get recent sessions sorted by last used.

        Args:
            limit: Maximum number of sessions
            context: Filter by context (optional)

        Returns:
            List of SessionInfo objects
        """

    @abstractmethod
    def get_last_interactive_session(self) -> Optional[str]:
        """Get the most recently used interactive session ID.

        Returns:
            Session ID or None
        """

    @abstractmethod
    def record_agent_use(self, session_id: str, agent: str, task: str) -> None:
        """Record agent activity in session.

        Args:
            session_id: Session UUID
            agent: Agent name
            task: Task description
        """

    @abstractmethod
    def cleanup_old_sessions(
        self, max_age_hours: int = 24, archive: bool = True
    ) -> int:
        """Remove or archive old sessions.

        Args:
            max_age_hours: Maximum age in hours
            archive: Whether to archive before removing

        Returns:
            Number of sessions cleaned up
        """

    @abstractmethod
    def archive_sessions(self, session_ids: List[str]) -> bool:
        """Archive specific sessions.

        Args:
            session_ids: List of session IDs to archive

        Returns:
            True if successful, False otherwise
        """


@dataclass
class SessionInfo:
    """Session information container."""

    id: str
    context: str = "default"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())
    use_count: int = 0
    agents_run: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "context": self.context,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "agents_run": self.agents_run,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionInfo":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            context=data.get("context", "default"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_used=data.get("last_used", datetime.now().isoformat()),
            use_count=data.get("use_count", 0),
            agents_run=data.get("agents_run", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionValidation:
    """Session validation results."""

    valid: bool
    session_id: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return bool(self.errors or self.warnings)


class SessionManager(ISessionManager):
    """Service for managing Claude session lifecycle."""

    def __init__(self, session_dir: Optional[Path] = None, config_service=None):
        """Initialize session manager.

        Args:
            session_dir: Directory to store session metadata
            config_service: Optional configuration service
        """
        self.session_dir = session_dir or Path.home() / ".claude-mpm" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.config_service = config_service
        self.logger = get_logger("SessionManager")
        self._sessions_cache: Dict[str, SessionInfo] = {}
        self._load_sessions()

    def create_session(
        self, context: str = "default", options: Optional[Dict[str, Any]] = None
    ) -> SessionInfo:
        """Create a new session with options.

        WHY: Creates a new session with unique ID and initializes metadata.
        This enables session tracking and context preservation.
        """
        session_id = str(uuid.uuid4())

        session = SessionInfo(id=session_id, context=context, metadata=options or {})

        self._sessions_cache[session_id] = session
        self._save_sessions()

        self.logger.info(f"Created session {session_id} for context: {context}")
        return session

    def load_session(self, session_id: str) -> Optional[SessionInfo]:
        """Load an existing session by ID.

        WHY: Retrieves session state from cache or disk for resumption.
        """
        # Check cache first
        if session_id in self._sessions_cache:
            return self._sessions_cache[session_id]

        # Try loading from disk
        self._load_sessions()
        return self._sessions_cache.get(session_id)

    def save_session(self, session_info: SessionInfo) -> bool:
        """Persist session state to storage.

        WHY: Ensures session state is preserved across application restarts.
        """
        try:
            self._sessions_cache[session_info.id] = session_info
            self._save_sessions()
            return True
        except Exception as e:
            self.logger.error(f"Failed to save session {session_info.id}: {e}")
            return False

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata.

        WHY: Provides session details for display and decision-making.
        """
        session = self.load_session(session_id)
        return session.to_dict() if session else None

    def validate_session(self, session_id: str) -> SessionValidation:
        """Validate session consistency and health.

        WHY: Ensures session data is consistent and usable before resumption.
        Checks for corruption, missing data, and age constraints.
        """
        validation = SessionValidation(valid=True, session_id=session_id)

        session = self.load_session(session_id)
        if not session:
            validation.valid = False
            validation.errors.append(f"Session {session_id} not found")
            return validation

        # Check session age
        try:
            created = datetime.fromisoformat(session.created_at)
            age = datetime.now() - created

            if age > timedelta(days=7):
                validation.warnings.append(f"Session is {age.days} days old")

            if age > timedelta(days=30):
                validation.valid = False
                validation.errors.append("Session too old (>30 days)")
        except (ValueError, TypeError) as e:
            validation.errors.append(f"Invalid timestamp: {e}")
            validation.valid = False

        # Check for required fields
        if not session.context:
            validation.errors.append("Missing session context")
            validation.valid = False

        # Check session file integrity
        session_file = self.session_dir / "active_sessions.json"
        if not session_file.exists():
            validation.warnings.append("Session file missing, will recreate")
        elif not session_file.stat().st_size:
            validation.errors.append("Session file is empty")
            validation.valid = False

        return validation

    def get_recent_sessions(
        self, limit: int = 10, context: Optional[str] = None
    ) -> List[SessionInfo]:
        """Get recent sessions sorted by last used.

        WHY: Enables users to easily resume recent sessions.
        """
        sessions = list(self._sessions_cache.values())

        # Filter by context if specified
        if context:
            sessions = [s for s in sessions if s.context == context]

        # Sort by last_used descending
        sessions.sort(key=lambda s: datetime.fromisoformat(s.last_used), reverse=True)

        return sessions[:limit]

    def get_last_interactive_session(self) -> Optional[str]:
        """Get the most recently used interactive session ID.

        WHY: For --resume without arguments, we want to resume the last
        interactive session (context="default").
        """
        recent = self.get_recent_sessions(limit=1, context="default")
        return recent[0].id if recent else None

    def record_agent_use(self, session_id: str, agent: str, task: str) -> None:
        """Record agent activity in session.

        WHY: Tracks which agents were used in a session for context
        preservation and debugging.
        """
        session = self.load_session(session_id)
        if not session:
            self.logger.warning(
                f"Cannot record agent use: session {session_id} not found"
            )
            return

        session.agents_run.append(
            {
                "agent": agent,
                "task": task[:100],  # Truncate long tasks
                "timestamp": datetime.now().isoformat(),
            }
        )
        session.last_used = datetime.now().isoformat()
        session.use_count += 1

        self.save_session(session)

    def cleanup_old_sessions(
        self, max_age_hours: int = 24, archive: bool = True
    ) -> int:
        """Remove or archive old sessions.

        WHY: Prevents unbounded growth of session data and improves performance.
        """
        now = datetime.now()
        max_age = timedelta(hours=max_age_hours)

        expired_ids = []
        for session_id, session in self._sessions_cache.items():
            try:
                created = datetime.fromisoformat(session.created_at)
                if now - created > max_age:
                    expired_ids.append(session_id)
            except (ValueError, TypeError):
                # Invalid timestamp, mark for cleanup
                expired_ids.append(session_id)

        if archive and expired_ids:
            self.archive_sessions(expired_ids)

        # Remove from cache
        for session_id in expired_ids:
            del self._sessions_cache[session_id]
            self.logger.info(f"Cleaned up expired session: {session_id}")

        if expired_ids:
            self._save_sessions()

        return len(expired_ids)

    def archive_sessions(self, session_ids: List[str]) -> bool:
        """Archive specific sessions.

        WHY: Preserves session history while reducing active memory usage.
        """
        if not session_ids:
            return True

        archive_dir = self.session_dir.parent / "archives" / "sessions"
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Collect sessions to archive
        sessions_to_archive = []
        for sid in session_ids:
            session = self.load_session(sid)
            if session:
                sessions_to_archive.append(session.to_dict())

        if not sessions_to_archive:
            return True

        # Create timestamped archive file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"sessions_archive_{timestamp}.json.gz"
        archive_path = archive_dir / archive_name

        try:
            # Compress and save sessions
            with gzip.open(archive_path, "wt", encoding="utf-8") as f:
                json.dump(sessions_to_archive, f, indent=2)

            self.logger.info(
                f"Archived {len(sessions_to_archive)} sessions to {archive_path}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to archive sessions: {e}")
            return False

    def _save_sessions(self) -> None:
        """Save sessions to disk.

        WHY: Persists session state for recovery after restart.
        """
        session_file = self.session_dir / "active_sessions.json"
        try:
            sessions_dict = {
                sid: session.to_dict() for sid, session in self._sessions_cache.items()
            }
            with open(session_file, "w") as f:
                json.dump(sessions_dict, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save sessions: {e}")

    def _load_sessions(self) -> None:
        """Load sessions from disk.

        WHY: Restores session state from persistent storage.
        """
        session_file = self.session_dir / "active_sessions.json"
        if not session_file.exists():
            return

        try:
            with open(session_file) as f:
                sessions_dict = json.load(f)

            self._sessions_cache = {
                sid: SessionInfo.from_dict(data) for sid, data in sessions_dict.items()
            }

            # Clean up old sessions on load
            self.cleanup_old_sessions(archive=True)
        except Exception as e:
            self.logger.error(f"Failed to load sessions: {e}")
            self._sessions_cache = {}


# Context manager for session management
class ManagedSession:
    """Context manager for session lifecycle.

    WHY: Provides a clean interface for session management with automatic
    cleanup and error handling.
    """

    def __init__(
        self,
        manager: ISessionManager,
        context: str = "default",
        options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize managed session.

        Args:
            manager: Session manager instance
            context: Session context
            options: Optional session configuration
        """
        self.manager = manager
        self.context = context
        self.options = options
        self.session: Optional[SessionInfo] = None

    def __enter__(self) -> SessionInfo:
        """Enter session context, return session info."""
        self.session = self.manager.create_session(self.context, self.options)
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit session context with cleanup."""
        if self.session:
            # Update last used time
            self.session.last_used = datetime.now().isoformat()
            self.manager.save_session(self.session)
