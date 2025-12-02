"""SQLite-based state tracking for agent sync operations.

This service manages sync state for agent files from Git sources, providing:
- Per-file SHA-256 content hash tracking
- Source metadata (URLs, last commit SHA, ETags)
- Complete sync history audit trail
- Change detection for efficient incremental updates

Database Location: ~/.config/claude-mpm/agent_sync.db
Thread Safety: Uses connection-per-operation pattern (safe for single-threaded use)
Performance: Optimized with indexes; expected <10ms per operation
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentSyncStateError(Exception):
    """Base exception for sync state errors."""


class DatabaseError(AgentSyncStateError):
    """Database operation errors."""


class AgentSyncState:
    """Service for tracking agent sync state in SQLite database.

    Responsibilities:
    - Manage SQLite connection lifecycle
    - Track per-file content hashes (SHA-256)
    - Record sync history with timestamps
    - Query file change status
    - Provide migration utilities

    Design Decision: Connection-per-operation pattern

    Rationale: Simplifies connection management and prevents connection leaks.
    SQLite allows concurrent reads but serializes writes, so connection pooling
    provides minimal benefit for our read-heavy workload.

    Trade-offs:
    - Simplicity: No pool management overhead
    - Safety: Automatic cleanup via context manager
    - Performance: Negligible overhead (<1ms per connection)

    Extension Points: Can add connection pooling if multi-threaded access needed.
    """

    # Schema version for migrations
    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize sync state service.

        Args:
            db_path: Path to SQLite database (defaults to ~/.config/claude-mpm/agent_sync.db)
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Default location: ~/.config/claude-mpm/agent_sync.db
            config_dir = Path.home() / ".config" / "claude-mpm"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = config_dir / "agent_sync.db"

        # Initialize database
        self._initialize_database()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections.

        Yields:
            sqlite3.Connection with foreign keys enabled and row factory

        Error Handling:
        - Exception during transaction: Rolls back automatically
        - Connection errors: Propagates to caller
        - Cleanup: Always closes connection
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        conn.execute("PRAGMA foreign_keys = ON")  # Enable FK constraints
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_database(self):
        """Initialize database schema if not exists.

        Creates all tables, indexes, and metadata on first run.
        Verifies schema version on subsequent runs.
        """
        with self._get_connection() as conn:
            # Check if database exists and has schema
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sources'"
            )
            if cursor.fetchone() is None:
                # Database is new, create schema
                self._create_schema(conn)
                logger.info(f"Initialized sync state database: {self.db_path}")
            else:
                # Verify schema version
                version = self._get_schema_version(conn)
                if version != self.SCHEMA_VERSION:
                    logger.warning(
                        f"Schema version mismatch: expected {self.SCHEMA_VERSION}, found {version}"
                    )
                    # TODO: Implement migration in future ticket

    def _create_schema(self, conn: sqlite3.Connection):
        """Create database schema with all tables and indexes.

        Schema Design:
        - sources: Track Git repositories or file sources
        - agent_files: Track individual files and content hashes
        - sync_history: Audit trail of all sync operations
        - schema_metadata: Schema versioning for migrations
        """
        conn.executescript(
            """
            -- Sources table: Track Git repositories or file sources
            CREATE TABLE sources (
                id TEXT PRIMARY KEY,                    -- Source identifier (e.g., "github-remote", "local-project")
                url TEXT NOT NULL,                      -- Source URL or file path
                last_sha TEXT,                          -- Last synced commit SHA (Git sources only)
                last_sync_time TEXT,                    -- ISO 8601 timestamp of last sync
                etag TEXT,                              -- HTTP ETag for GitHub raw URLs
                enabled INTEGER DEFAULT 1,              -- 0=disabled, 1=enabled
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Agent files table: Track individual files and content hashes
            CREATE TABLE agent_files (
                source_id TEXT NOT NULL,                -- FK to sources.id
                file_path TEXT NOT NULL,                -- Relative path (e.g., "research.md")
                content_sha TEXT NOT NULL,              -- SHA-256 hash of file content
                local_path TEXT,                        -- Absolute path to cached file
                synced_at TEXT NOT NULL,                -- ISO 8601 timestamp when file was synced
                file_size INTEGER,                      -- File size in bytes
                PRIMARY KEY (source_id, file_path),
                FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
            );

            -- Sync history table: Audit trail of all sync operations
            CREATE TABLE sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,                -- FK to sources.id
                sync_time TEXT NOT NULL,                -- ISO 8601 timestamp
                status TEXT NOT NULL,                   -- 'success', 'partial', 'error'
                files_synced INTEGER DEFAULT 0,         -- Number of files downloaded
                files_cached INTEGER DEFAULT 0,         -- Number of cache hits
                files_failed INTEGER DEFAULT 0,         -- Number of failed downloads
                error_message TEXT,                     -- Error details if status='error'
                duration_ms INTEGER,                    -- Sync duration in milliseconds
                FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
            );

            -- Performance indexes
            CREATE INDEX idx_agent_files_source ON agent_files(source_id);
            CREATE INDEX idx_agent_files_path ON agent_files(file_path);
            CREATE INDEX idx_sync_history_source_time ON sync_history(source_id, sync_time DESC);
            CREATE INDEX idx_sync_history_status ON sync_history(status);

            -- Metadata table for schema versioning
            CREATE TABLE schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            INSERT INTO schema_metadata (key, value) VALUES ('version', '1');
            INSERT INTO schema_metadata (key, value) VALUES ('created_at', datetime('now'));
        """
        )

    def _get_schema_version(self, conn: sqlite3.Connection) -> int:
        """Get current schema version.

        Args:
            conn: Database connection

        Returns:
            Schema version number (0 if schema_metadata table doesn't exist)
        """
        try:
            cursor = conn.execute(
                "SELECT value FROM schema_metadata WHERE key = 'version'"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        except sqlite3.OperationalError:
            return 0

    # ==============================================================================
    # SOURCE MANAGEMENT
    # ==============================================================================

    def register_source(self, source_id: str, url: str, enabled: bool = True) -> None:
        """Register or update a sync source.

        Args:
            source_id: Unique source identifier (e.g., "github-remote")
            url: Source URL or file path
            enabled: Whether source is enabled for sync

        Example:
            sync_state.register_source(
                source_id="github-remote",
                url="https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main",
                enabled=True
            )
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sources (id, url, enabled, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    url = excluded.url,
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at
                """,
                (source_id, url, int(enabled), datetime.now(timezone.utc).isoformat()),
            )
        logger.debug(f"Registered source: {source_id} -> {url}")

    def update_source_sync_metadata(
        self,
        source_id: str,
        last_sha: Optional[str] = None,
        etag: Optional[str] = None,
    ) -> None:
        """Update source sync metadata (commit SHA, ETag).

        Args:
            source_id: Source identifier
            last_sha: Latest commit SHA (Git sources)
            etag: HTTP ETag (GitHub raw URLs)

        Example:
            sync_state.update_source_sync_metadata(
                source_id="github-remote",
                last_sha="abc123def456",
                etag='"W/abc123"'
            )
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE sources
                SET last_sha = ?, etag = ?, last_sync_time = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    last_sha,
                    etag,
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    source_id,
                ),
            )
        logger.debug(f"Updated source metadata: {source_id}")

    def get_source_info(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get source metadata.

        Args:
            source_id: Source identifier

        Returns:
            Source metadata dict or None if not found

        Example:
            >>> info = sync_state.get_source_info("github-remote")
            >>> print(info["url"])
            https://raw.githubusercontent.com/...
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_sources(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Get all registered sources.

        Args:
            enabled_only: Only return enabled sources

        Returns:
            List of source metadata dicts
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM sources"
            if enabled_only:
                query += " WHERE enabled = 1"
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    # ==============================================================================
    # FILE TRACKING
    # ==============================================================================

    def track_file(
        self,
        source_id: str,
        file_path: str,
        content_sha: str,
        local_path: Optional[str] = None,
        file_size: Optional[int] = None,
    ) -> None:
        """Track agent file with content hash.

        Args:
            source_id: Source identifier
            file_path: Relative file path (e.g., "research.md")
            content_sha: SHA-256 hash of file content
            local_path: Absolute path to cached file
            file_size: File size in bytes

        Example:
            sync_state.track_file(
                source_id="github-remote",
                file_path="research.md",
                content_sha="abc123def456...",
                local_path="/home/user/.claude-mpm/cache/research.md",
                file_size=2048
            )
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_files (source_id, file_path, content_sha, local_path, synced_at, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, file_path) DO UPDATE SET
                    content_sha = excluded.content_sha,
                    local_path = excluded.local_path,
                    synced_at = excluded.synced_at,
                    file_size = excluded.file_size
                """,
                (
                    source_id,
                    file_path,
                    content_sha,
                    local_path,
                    datetime.now(timezone.utc).isoformat(),
                    file_size,
                ),
            )
        logger.debug(f"Tracked file: {source_id}/{file_path} -> {content_sha[:8]}...")

    def get_file_hash(self, source_id: str, file_path: str) -> Optional[str]:
        """Get stored content hash for file.

        Args:
            source_id: Source identifier
            file_path: Relative file path

        Returns:
            SHA-256 hash or None if not tracked
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT content_sha FROM agent_files WHERE source_id = ? AND file_path = ?",
                (source_id, file_path),
            )
            row = cursor.fetchone()
            return row["content_sha"] if row else None

    def has_file_changed(
        self, source_id: str, file_path: str, current_sha: str
    ) -> bool:
        """Check if file content has changed.

        Args:
            source_id: Source identifier
            file_path: Relative file path
            current_sha: Current SHA-256 hash

        Returns:
            True if changed or not tracked, False if unchanged

        Example:
            >>> changed = sync_state.has_file_changed(
            ...     "github-remote", "research.md", "abc123..."
            ... )
            >>> if changed:
            ...     print("File needs update")
        """
        stored_sha = self.get_file_hash(source_id, file_path)
        if stored_sha is None:
            return True  # Not tracked = changed
        return stored_sha != current_sha

    # ==============================================================================
    # SYNC HISTORY
    # ==============================================================================

    def record_sync_result(
        self,
        source_id: str,
        status: str,
        files_synced: int = 0,
        files_cached: int = 0,
        files_failed: int = 0,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> int:
        """Record sync operation result.

        Args:
            source_id: Source identifier
            status: 'success', 'partial', or 'error'
            files_synced: Number of files downloaded
            files_cached: Number of cache hits
            files_failed: Number of failed downloads
            error_message: Error details if status='error'
            duration_ms: Sync duration in milliseconds

        Returns:
            Sync history record ID

        Example:
            record_id = sync_state.record_sync_result(
                source_id="github-remote",
                status="success",
                files_synced=5,
                files_cached=3,
                duration_ms=1500
            )
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sync_history (
                    source_id, sync_time, status, files_synced, files_cached,
                    files_failed, error_message, duration_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    datetime.now(timezone.utc).isoformat(),
                    status,
                    files_synced,
                    files_cached,
                    files_failed,
                    error_message,
                    duration_ms,
                ),
            )
            return cursor.lastrowid

    def get_sync_history(self, source_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sync history for source.

        Args:
            source_id: Source identifier
            limit: Maximum number of records

        Returns:
            List of sync history records (most recent first)

        Example:
            >>> history = sync_state.get_sync_history("github-remote", limit=5)
            >>> for record in history:
            ...     print(f"{record['sync_time']}: {record['status']}")
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sync_history
                WHERE source_id = ?
                ORDER BY sync_time DESC
                LIMIT ?
                """,
                (source_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_history(self, days: int = 30) -> int:
        """Remove sync history older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of records deleted

        Example:
            deleted = sync_state.cleanup_old_history(days=30)
            print(f"Cleaned up {deleted} old sync records")
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sync_history WHERE sync_time < ?", (cutoff,)
            )
            deleted = cursor.rowcount

        logger.info(f"Cleaned up {deleted} sync history records older than {days} days")
        return deleted
