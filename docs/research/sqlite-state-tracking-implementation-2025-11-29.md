# SQLite State Tracking Implementation Research (1M-388)

**Research Date:** 2025-11-29
**Ticket:** 1M-388 - Implement SQLite state tracking for agent sync
**Parent Issue:** 1M-382 - Multi-source agent management system
**Researcher:** Research Agent
**Status:** Technical Specification Complete

---

## Executive Summary

This research provides comprehensive technical guidance for implementing SQLite-based state tracking for agent sync operations. The implementation will replace the current JSON-based ETag cache in `GitSourceSyncService` with a robust relational database supporting per-file content hash tracking, commit SHA tracking, and complete sync history audit trails.

**Key Findings:**
- ✅ GitSourceSyncService currently uses JSON file for ETag storage only
- ✅ Standard library `sqlite3` is appropriate (no ORM needed)
- ✅ Clear integration point identified: Replace ETagCache class
- ✅ Existing file hash utility available: `get_file_hash()` from `file_utils.py`
- ✅ Service base classes provide patterns to follow
- ✅ Database location: `~/.config/claude-mpm/agent_sync.db`

**Effort Estimate:** 8-12 hours development + 4-6 hours testing

---

## 1. Database Schema Design

### 1.1 Complete Schema DDL

```sql
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
```

### 1.2 Schema Design Rationale

**Decision: Use TEXT for timestamps instead of DATETIME**
- Rationale: SQLite stores DATETIME as TEXT internally anyway; using TEXT with ISO 8601 format provides better Python integration and clarity
- Trade-off: Manual date parsing required, but `datetime.fromisoformat()` handles this efficiently

**Decision: Composite PRIMARY KEY for agent_files**
- Rationale: Natural key (source_id, file_path) ensures uniqueness and prevents duplicate tracking
- Trade-off: Slightly larger index than surrogate key, but improves query performance

**Decision: Foreign key constraints with CASCADE**
- Rationale: Automatic cleanup when source is removed prevents orphaned records
- Trade-off: Requires enabling foreign keys (not default in SQLite)

**Decision: Separate sync_history table**
- Rationale: Preserves complete audit trail; supports debugging and sync analytics
- Trade-off: Additional storage, but negligible (<1KB per sync)

---

## 2. Service Architecture

### 2.1 AgentSyncState Service Design

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/agent_sync_state.py`

```python
"""SQLite-based state tracking for agent sync operations."""

import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

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

    Database Location: ~/.config/claude-mpm/agent_sync.db

    Thread Safety: Uses connection-per-operation pattern (safe for single-threaded use)
    Performance: Optimized with indexes; expected <10ms per operation
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
            sqlite3.Connection with foreign keys enabled
        """
        conn = sqlite3.connect(self.db_path)
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
        """Initialize database schema if not exists."""
        # Create database and schema
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
        """Create database schema."""
        # [Full schema DDL from Section 1.1]
        conn.executescript("""
            -- [Insert complete schema DDL here]
        """)

    def _get_schema_version(self, conn: sqlite3.Connection) -> int:
        """Get current schema version."""
        try:
            cursor = conn.execute(
                "SELECT value FROM schema_metadata WHERE key = 'version'"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        except sqlite3.OperationalError:
            return 0

    # CRUD Operations

    def register_source(
        self, source_id: str, url: str, enabled: bool = True
    ) -> None:
        """Register or update a sync source.

        Args:
            source_id: Unique source identifier
            url: Source URL or file path
            enabled: Whether source is enabled for sync
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
        """
        stored_sha = self.get_file_hash(source_id, file_path)
        if stored_sha is None:
            return True  # Not tracked = changed
        return stored_sha != current_sha

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

    def get_sync_history(
        self, source_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent sync history for source.

        Args:
            source_id: Source identifier
            limit: Maximum number of records

        Returns:
            List of sync history records
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

    def get_source_info(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get source metadata.

        Args:
            source_id: Source identifier

        Returns:
            Source metadata dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM sources WHERE id = ?", (source_id,)
            )
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

    def cleanup_old_history(self, days: int = 30) -> int:
        """Remove sync history older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of records deleted
        """
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sync_history WHERE sync_time < ?", (cutoff,)
            )
            deleted = cursor.rowcount

        logger.info(f"Cleaned up {deleted} sync history records older than {days} days")
        return deleted
```

### 2.2 Service Comparison with Existing Patterns

**Follows ConfigServiceBase Pattern:**
- ✅ Uses standard `__init__` with optional config
- ✅ Implements logger via class attribute
- ✅ Uses Path objects for file paths
- ✅ Handles errors gracefully with custom exceptions

**Follows LifecycleServiceBase Pattern:**
- ⚠️ Simplified lifecycle (no state machine needed for database service)
- ✅ Uses context managers for resource management
- ✅ Implements health/status via `get_source_info()`

**Key Differences:**
- Uses connection-per-operation pattern (simpler than connection pooling)
- No async support (SQLite is synchronous; async wrapper not needed for current use case)
- Read-heavy operations (queries) vs. write-heavy (updates) both optimized

---

## 3. Integration Points

### 3.1 GitSourceSyncService Integration

**Current Implementation (JSON-based):**
```python
# Lines 34-138 in git_source_sync_service.py
class ETagCache:
    """Manages ETag storage for efficient HTTP caching."""

    def __init__(self, cache_file: Path):
        self._cache_file = cache_file
        self._cache: Dict[str, Dict[str, Any]] = self._load_cache()

    def get_etag(self, url: str) -> Optional[str]:
        # Returns ETag from JSON file

    def set_etag(self, url: str, etag: str, file_size: Optional[int] = None):
        # Writes ETag to JSON file
```

**Proposed Integration (SQLite-based):**
```python
# Updated GitSourceSyncService.__init__
def __init__(
    self,
    source_url: str = "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main",
    cache_dir: Optional[Path] = None,
    source_id: str = "github-remote",  # NEW: Source identifier
):
    self.source_url = source_url.rstrip("/")
    self.source_id = source_id  # NEW

    # Setup cache directory (unchanged)
    if cache_dir:
        self.cache_dir = Path(cache_dir)
    else:
        home = Path.home()
        self.cache_dir = home / ".claude-mpm" / "cache" / "remote-agents"

    self.cache_dir.mkdir(parents=True, exist_ok=True)

    # Setup HTTP session (unchanged)
    self.session = requests.Session()
    self.session.headers["Accept"] = "text/plain"

    # REPLACE: ETag cache with AgentSyncState
    # OLD: self.etag_cache = ETagCache(etag_cache_file)
    # NEW:
    from claude_mpm.services.agents.sources.agent_sync_state import AgentSyncState
    self.sync_state = AgentSyncState()

    # Register this source
    self.sync_state.register_source(
        source_id=self.source_id,
        url=self.source_url,
        enabled=True
    )
```

**Updated sync_agents() Method:**
```python
def sync_agents(self, force_refresh: bool = False) -> Dict[str, Any]:
    """Sync agents from remote Git repository."""
    import time
    from claude_mpm.core.file_utils import get_file_hash

    logger.info(f"Starting agent sync from {self.source_url}")
    start_time = time.time()

    results = {
        "synced": [],
        "cached": [],
        "failed": [],
        "total_downloaded": 0,
        "cache_hits": 0,
    }

    agent_list = self._get_agent_list()

    for agent_filename in agent_list:
        try:
            url = f"{self.source_url}/{agent_filename}"

            # Fetch with ETag check
            content, status = self._fetch_with_etag(url, force_refresh)

            if status == 200:
                # New content downloaded - save and track
                cache_file = self.cache_dir / agent_filename
                self._save_to_cache(agent_filename, content)

                # NEW: Calculate and track content hash
                content_sha = get_file_hash(cache_file, algorithm="sha256")
                self.sync_state.track_file(
                    source_id=self.source_id,
                    file_path=agent_filename,
                    content_sha=content_sha,
                    local_path=str(cache_file),
                    file_size=len(content.encode("utf-8"))
                )

                results["synced"].append(agent_filename)
                results["total_downloaded"] += 1
                logger.info(f"Downloaded: {agent_filename}")

            elif status == 304:
                # Not modified - verify hash
                cache_file = self.cache_dir / agent_filename
                if cache_file.exists():
                    current_sha = get_file_hash(cache_file, algorithm="sha256")
                    if self.sync_state.has_file_changed(
                        self.source_id, agent_filename, current_sha
                    ):
                        # Hash mismatch - re-download
                        logger.warning(
                            f"Hash mismatch for {agent_filename}, re-downloading"
                        )
                        content, _ = self._fetch_with_etag(url, force_refresh=True)
                        # [Save and track as above]
                    else:
                        # Hash matches - true cache hit
                        results["cached"].append(agent_filename)
                        results["cache_hits"] += 1
                        logger.debug(f"Cache hit: {agent_filename}")

            else:
                # Error status
                logger.warning(f"Unexpected status {status} for {agent_filename}")
                results["failed"].append(agent_filename)

        except requests.RequestException as e:
            logger.error(f"Network error downloading {agent_filename}: {e}")
            results["failed"].append(agent_filename)
        except Exception as e:
            logger.error(f"Unexpected error for {agent_filename}: {e}")
            results["failed"].append(agent_filename)

    # Record sync result
    duration_ms = int((time.time() - start_time) * 1000)
    status = "success" if not results["failed"] else (
        "partial" if results["synced"] or results["cached"] else "error"
    )

    self.sync_state.record_sync_result(
        source_id=self.source_id,
        status=status,
        files_synced=results["total_downloaded"],
        files_cached=results["cache_hits"],
        files_failed=len(results["failed"]),
        duration_ms=duration_ms
    )

    # Update source metadata
    # NOTE: Commit SHA tracking requires GitHub API integration (future ticket)
    self.sync_state.update_source_sync_metadata(
        source_id=self.source_id,
        etag=None,  # ETag now stored per-file, not per-source
    )

    logger.info(
        f"Sync complete: {results['total_downloaded']} downloaded, "
        f"{results['cache_hits']} from cache, {len(results['failed'])} failed"
    )

    return results
```

**Updated _fetch_with_etag() Method:**
```python
def _fetch_with_etag(
    self, url: str, force_refresh: bool = False
) -> Tuple[Optional[str], int]:
    """Fetch URL with ETag caching."""
    headers = {}

    # Extract filename from URL
    filename = url.split("/")[-1]

    # Get stored ETag from source metadata (not per-file)
    if not force_refresh:
        source_info = self.sync_state.get_source_info(self.source_id)
        if source_info and source_info.get("etag"):
            headers["If-None-Match"] = source_info["etag"]

    response = self.session.get(url, headers=headers, timeout=30)

    if response.status_code == 304:
        return None, 304

    if response.status_code == 200:
        content = response.text
        etag = response.headers.get("ETag")

        # Update source-level ETag
        if etag:
            self.sync_state.update_source_sync_metadata(
                source_id=self.source_id,
                etag=etag
            )

        return content, 200

    return None, response.status_code
```

### 3.2 Required File Changes

**New Files:**
1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/agent_sync_state.py`
   - AgentSyncState service class
   - Custom exceptions
   - ~500 lines

**Modified Files:**
1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/git_source_sync_service.py`
   - Replace ETagCache with AgentSyncState
   - Add content hash tracking
   - Update sync_agents() method
   - Update _fetch_with_etag() method
   - ~150 lines changed

2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/__init__.py`
   - Add AgentSyncState export
   - ~2 lines changed

**Migration Script:**
1. `/Users/masa/Projects/claude-mpm/scripts/migrate_etag_cache_to_sqlite.py`
   - One-time migration utility
   - Read existing `.etag-cache.json`
   - Populate SQLite database
   - ~100 lines

### 3.3 Backward Compatibility

**Decision: Keep ETagCache for backward compatibility during transition**

**Approach:**
1. Phase 1 (1M-388): Implement AgentSyncState, update GitSourceSyncService to use it
2. Phase 2 (Future): Add deprecation warning to ETagCache
3. Phase 3 (Future): Remove ETagCache entirely

**Compatibility Layer:**
```python
# git_source_sync_service.py
def __init__(self, ...):
    # NEW: Use SQLite by default
    self.sync_state = AgentSyncState()

    # OLD: Keep ETag cache for migration period
    # Check if old cache exists and migrate
    etag_cache_file = self.cache_dir / ".etag-cache.json"
    if etag_cache_file.exists():
        logger.info("Migrating ETag cache to SQLite...")
        self._migrate_etag_cache(etag_cache_file)
        # Rename old cache to prevent re-migration
        etag_cache_file.rename(etag_cache_file.with_suffix(".json.migrated"))

def _migrate_etag_cache(self, cache_file: Path):
    """Migrate old ETag cache to SQLite."""
    import json

    try:
        with cache_file.open() as f:
            old_cache = json.load(f)

        for url, metadata in old_cache.items():
            filename = url.split("/")[-1]
            etag = metadata.get("etag")
            if etag:
                # Store in new system
                self.sync_state.update_source_sync_metadata(
                    source_id=self.source_id,
                    etag=etag
                )

        logger.info("ETag cache migration complete")
    except Exception as e:
        logger.error(f"Failed to migrate ETag cache: {e}")
```

---

## 4. Migration Strategy

### 4.1 Migration Script

**Purpose:** One-time migration for existing installations

**Script:** `/Users/masa/Projects/claude-mpm/scripts/migrate_etag_cache_to_sqlite.py`

```python
#!/usr/bin/env python3
"""Migrate ETag cache from JSON to SQLite.

Usage:
    python scripts/migrate_etag_cache_to_sqlite.py [--dry-run]
"""

import argparse
import json
import logging
from pathlib import Path

from claude_mpm.services.agents.sources.agent_sync_state import AgentSyncState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_etag_cache(cache_dir: Path, dry_run: bool = False):
    """Migrate ETag cache to SQLite.

    Args:
        cache_dir: Directory containing .etag-cache.json
        dry_run: If True, only show what would be migrated
    """
    etag_cache_file = cache_dir / ".etag-cache.json"

    if not etag_cache_file.exists():
        logger.warning(f"No ETag cache found at {etag_cache_file}")
        return

    # Load old cache
    try:
        with etag_cache_file.open() as f:
            old_cache = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in ETag cache: {e}")
        return

    logger.info(f"Found {len(old_cache)} entries in old ETag cache")

    if dry_run:
        logger.info("DRY RUN - would migrate:")
        for url, metadata in old_cache.items():
            logger.info(f"  {url} -> ETag: {metadata.get('etag')}")
        return

    # Initialize new system
    sync_state = AgentSyncState()

    # Register default source
    source_id = "github-remote"
    sync_state.register_source(
        source_id=source_id,
        url="https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main",
        enabled=True
    )

    # Migrate entries
    migrated = 0
    for url, metadata in old_cache.items():
        try:
            etag = metadata.get("etag")
            if etag:
                sync_state.update_source_sync_metadata(
                    source_id=source_id,
                    etag=etag
                )
                migrated += 1
        except Exception as e:
            logger.error(f"Failed to migrate {url}: {e}")

    logger.info(f"Migrated {migrated} ETag entries to SQLite")

    # Backup old cache
    backup_file = etag_cache_file.with_suffix(".json.backup")
    etag_cache_file.rename(backup_file)
    logger.info(f"Backed up old cache to {backup_file}")


def main():
    parser = argparse.ArgumentParser(description="Migrate ETag cache to SQLite")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".claude-mpm" / "cache" / "remote-agents",
        help="Cache directory (default: ~/.claude-mpm/cache/remote-agents/)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )

    args = parser.parse_args()

    migrate_etag_cache(args.cache_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
```

### 4.2 Migration Testing

**Test Cases:**
1. Empty ETag cache (new installation)
2. Valid ETag cache with 10 entries
3. Corrupted JSON cache file
4. Missing cache file
5. Read-only cache directory

**Success Criteria:**
- All valid entries migrated successfully
- Old cache backed up with `.json.backup` extension
- No data loss during migration
- Migration idempotent (safe to run multiple times)

---

## 5. Testing Strategy

### 5.1 Unit Tests

**File:** `/Users/masa/Projects/claude-mpm/tests/services/agents/sources/test_agent_sync_state.py`

**Test Coverage (Target: 85%+):**

```python
"""Unit tests for AgentSyncState service."""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from claude_mpm.services.agents.sources.agent_sync_state import (
    AgentSyncState,
    AgentSyncStateError,
    DatabaseError,
)


@pytest.fixture
def temp_db(tmp_path):
    """Temporary database for testing."""
    db_path = tmp_path / "test_sync.db"
    yield db_path
    # Cleanup handled by tmp_path


@pytest.fixture
def sync_state(temp_db):
    """AgentSyncState instance with temporary database."""
    return AgentSyncState(db_path=temp_db)


class TestAgentSyncStateInitialization:
    """Test database initialization."""

    def test_creates_database_file(self, temp_db):
        """Test database file creation."""
        assert not temp_db.exists()

        sync_state = AgentSyncState(db_path=temp_db)

        assert temp_db.exists()

    def test_creates_all_tables(self, sync_state, temp_db):
        """Test all required tables created."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "sources" in tables
        assert "agent_files" in tables
        assert "sync_history" in tables
        assert "schema_metadata" in tables

    def test_creates_indexes(self, sync_state, temp_db):
        """Test performance indexes created."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "idx_agent_files_source" in indexes
        assert "idx_agent_files_path" in indexes
        assert "idx_sync_history_source_time" in indexes

    def test_sets_schema_version(self, sync_state, temp_db):
        """Test schema version metadata."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT value FROM schema_metadata WHERE key='version'"
        )
        version = cursor.fetchone()[0]
        conn.close()

        assert version == "1"

    def test_enables_foreign_keys(self, sync_state, temp_db):
        """Test foreign key constraints enabled."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("PRAGMA foreign_keys")
        fk_enabled = cursor.fetchone()[0]
        conn.close()

        # Note: FK pragma returns 0 outside of transaction
        # Test cascade behavior instead
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file("test-source", "test.md", "sha123")

        # Delete source should cascade to agent_files
        with sync_state._get_connection() as conn:
            conn.execute("DELETE FROM sources WHERE id='test-source'")

        # Verify file record deleted
        assert sync_state.get_file_hash("test-source", "test.md") is None


class TestSourceManagement:
    """Test source CRUD operations."""

    def test_register_new_source(self, sync_state):
        """Test registering new source."""
        sync_state.register_source(
            source_id="test-source",
            url="https://github.com/test/repo",
            enabled=True
        )

        source = sync_state.get_source_info("test-source")
        assert source is not None
        assert source["url"] == "https://github.com/test/repo"
        assert source["enabled"] == 1

    def test_register_source_idempotent(self, sync_state):
        """Test re-registering source updates it."""
        sync_state.register_source("test-source", "https://old.url")
        sync_state.register_source("test-source", "https://new.url")

        source = sync_state.get_source_info("test-source")
        assert source["url"] == "https://new.url"

    def test_update_source_metadata(self, sync_state):
        """Test updating source sync metadata."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.update_source_sync_metadata(
            source_id="test-source",
            last_sha="abc123",
            etag='"xyz789"'
        )

        source = sync_state.get_source_info("test-source")
        assert source["last_sha"] == "abc123"
        assert source["etag"] == '"xyz789"'
        assert source["last_sync_time"] is not None

    def test_get_all_sources(self, sync_state):
        """Test retrieving all sources."""
        sync_state.register_source("source1", "https://example.com/1", enabled=True)
        sync_state.register_source("source2", "https://example.com/2", enabled=False)

        all_sources = sync_state.get_all_sources()
        assert len(all_sources) == 2

        enabled_only = sync_state.get_all_sources(enabled_only=True)
        assert len(enabled_only) == 1
        assert enabled_only[0]["id"] == "source1"


class TestFileTracking:
    """Test agent file tracking."""

    def test_track_new_file(self, sync_state):
        """Test tracking new agent file."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file(
            source_id="test-source",
            file_path="research.md",
            content_sha="abc123def456",
            local_path="/tmp/research.md",
            file_size=1024
        )

        stored_sha = sync_state.get_file_hash("test-source", "research.md")
        assert stored_sha == "abc123def456"

    def test_track_file_updates_existing(self, sync_state):
        """Test updating tracked file."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file("test-source", "test.md", "old-sha")
        sync_state.track_file("test-source", "test.md", "new-sha")

        stored_sha = sync_state.get_file_hash("test-source", "test.md")
        assert stored_sha == "new-sha"

    def test_has_file_changed_new_file(self, sync_state):
        """Test change detection for new file."""
        sync_state.register_source("test-source", "https://example.com")

        changed = sync_state.has_file_changed("test-source", "new.md", "any-sha")
        assert changed is True

    def test_has_file_changed_unchanged(self, sync_state):
        """Test change detection for unchanged file."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file("test-source", "test.md", "same-sha")

        changed = sync_state.has_file_changed("test-source", "test.md", "same-sha")
        assert changed is False

    def test_has_file_changed_modified(self, sync_state):
        """Test change detection for modified file."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file("test-source", "test.md", "old-sha")

        changed = sync_state.has_file_changed("test-source", "test.md", "new-sha")
        assert changed is True


class TestSyncHistory:
    """Test sync history recording."""

    def test_record_successful_sync(self, sync_state):
        """Test recording successful sync."""
        sync_state.register_source("test-source", "https://example.com")

        record_id = sync_state.record_sync_result(
            source_id="test-source",
            status="success",
            files_synced=5,
            files_cached=3,
            files_failed=0,
            duration_ms=1500
        )

        assert record_id > 0

        history = sync_state.get_sync_history("test-source", limit=1)
        assert len(history) == 1
        assert history[0]["status"] == "success"
        assert history[0]["files_synced"] == 5
        assert history[0]["duration_ms"] == 1500

    def test_record_failed_sync(self, sync_state):
        """Test recording failed sync."""
        sync_state.register_source("test-source", "https://example.com")

        sync_state.record_sync_result(
            source_id="test-source",
            status="error",
            files_synced=0,
            files_failed=10,
            error_message="Network timeout"
        )

        history = sync_state.get_sync_history("test-source")
        assert history[0]["error_message"] == "Network timeout"

    def test_get_sync_history_ordering(self, sync_state):
        """Test sync history returned in descending order."""
        sync_state.register_source("test-source", "https://example.com")

        # Record multiple syncs
        for i in range(5):
            sync_state.record_sync_result(
                source_id="test-source",
                status="success",
                files_synced=i
            )

        history = sync_state.get_sync_history("test-source", limit=5)

        # Most recent first
        assert history[0]["files_synced"] == 4
        assert history[4]["files_synced"] == 0

    def test_cleanup_old_history(self, sync_state):
        """Test cleaning up old sync history."""
        from datetime import timedelta

        sync_state.register_source("test-source", "https://example.com")

        # Insert old record directly (mocking timestamp)
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with sync_state._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sync_history (source_id, sync_time, status)
                VALUES (?, ?, ?)
                """,
                ("test-source", old_time, "success")
            )

        # Insert recent record
        sync_state.record_sync_result("test-source", "success")

        # Cleanup records older than 30 days
        deleted = sync_state.cleanup_old_history(days=30)

        assert deleted == 1

        # Recent record should remain
        history = sync_state.get_sync_history("test-source")
        assert len(history) == 1


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_get_nonexistent_source(self, sync_state):
        """Test querying nonexistent source."""
        source = sync_state.get_source_info("nonexistent")
        assert source is None

    def test_get_nonexistent_file_hash(self, sync_state):
        """Test querying nonexistent file."""
        sync_state.register_source("test-source", "https://example.com")

        sha = sync_state.get_file_hash("test-source", "nonexistent.md")
        assert sha is None

    def test_track_file_without_source(self, sync_state):
        """Test tracking file for unregistered source."""
        with pytest.raises(sqlite3.IntegrityError):
            with sync_state._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO agent_files (source_id, file_path, content_sha, synced_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("nonexistent-source", "test.md", "sha", datetime.now(timezone.utc).isoformat())
                )

    def test_foreign_key_cascade_delete(self, sync_state):
        """Test CASCADE delete removes dependent records."""
        sync_state.register_source("test-source", "https://example.com")
        sync_state.track_file("test-source", "test.md", "sha123")
        sync_state.record_sync_result("test-source", "success")

        # Delete source
        with sync_state._get_connection() as conn:
            conn.execute("DELETE FROM sources WHERE id='test-source'")

        # Verify cascaded deletions
        assert sync_state.get_file_hash("test-source", "test.md") is None
        assert len(sync_state.get_sync_history("test-source")) == 0
```

**Coverage Target:** 85%+

**Critical Paths:**
- ✅ Database initialization
- ✅ Schema creation
- ✅ All CRUD operations
- ✅ Foreign key cascades
- ✅ Error handling
- ✅ Transaction rollback

### 5.2 Integration Tests

**File:** `/Users/masa/Projects/claude-mpm/tests/services/agents/sources/test_git_source_sync_integration.py`

```python
"""Integration tests for GitSourceSyncService with AgentSyncState."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import requests

from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)
from claude_mpm.services.agents.sources.agent_sync_state import AgentSyncState


@pytest.fixture
def temp_cache(tmp_path):
    """Temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def temp_db(tmp_path):
    """Temporary database."""
    return tmp_path / "test_sync.db"


@pytest.fixture
def mock_service(temp_cache, temp_db, monkeypatch):
    """GitSourceSyncService with mocked HTTP and temp database."""
    # Patch AgentSyncState to use temp database
    original_init = AgentSyncState.__init__

    def mock_init(self, db_path=None):
        original_init(self, db_path=temp_db)

    monkeypatch.setattr(AgentSyncState, "__init__", mock_init)

    service = GitSourceSyncService(
        source_url="https://raw.githubusercontent.com/test/repo/main",
        cache_dir=temp_cache,
        source_id="test-source"
    )

    return service


class TestGitSourceSyncWithState:
    """Test GitSourceSyncService integration with AgentSyncState."""

    @patch("requests.Session.get")
    def test_sync_downloads_and_tracks_files(self, mock_get, mock_service, temp_cache):
        """Test sync downloads files and tracks content hashes."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "# Research Agent\n\nContent here"
        mock_response.headers = {"ETag": '"abc123"'}
        mock_get.return_value = mock_response

        # Sync agents
        results = mock_service.sync_agents()

        # Verify download
        assert results["total_downloaded"] > 0

        # Verify file tracked in database
        from claude_mpm.core.file_utils import get_file_hash

        for filename in results["synced"]:
            cache_file = temp_cache / filename
            assert cache_file.exists()

            # Verify hash tracked
            expected_sha = get_file_hash(cache_file, algorithm="sha256")
            stored_sha = mock_service.sync_state.get_file_hash(
                "test-source", filename
            )
            assert stored_sha == expected_sha

    @patch("requests.Session.get")
    def test_sync_detects_unchanged_files(self, mock_get, mock_service, temp_cache):
        """Test sync correctly uses cached files when unchanged."""
        # First sync - download
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "# Content"
        mock_response.headers = {"ETag": '"v1"'}
        mock_get.return_value = mock_response

        results1 = mock_service.sync_agents()

        # Second sync - 304 Not Modified
        mock_response.status_code = 304
        results2 = mock_service.sync_agents()

        # Verify cache hits
        assert results2["cache_hits"] > 0
        assert results2["total_downloaded"] == 0

    @patch("requests.Session.get")
    def test_sync_records_history(self, mock_get, mock_service):
        """Test sync operations recorded in history."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "# Content"
        mock_response.headers = {"ETag": '"v1"'}
        mock_get.return_value = mock_response

        # Perform sync
        mock_service.sync_agents()

        # Check history
        history = mock_service.sync_state.get_sync_history("test-source")

        assert len(history) >= 1
        assert history[0]["status"] in ["success", "partial"]
        assert history[0]["duration_ms"] is not None
```

---

## 6. Performance Considerations

### 6.1 Expected Performance

**Database Operations:**
- Insert/Update: <5ms per operation
- Query: <2ms per operation
- Batch operations: <50ms for 10 files
- Full sync (10 agents): <100ms database overhead

**Memory Usage:**
- SQLite connection: ~1MB
- In-memory row cache: ~10KB per 100 records
- Total overhead: <5MB

**Disk Usage:**
- Schema + indexes: ~100KB
- Per source: ~1KB
- Per file: ~200 bytes
- Per sync history: ~300 bytes
- **Estimated total (100 agents, 50 sync cycles):** ~50KB

### 6.2 Optimization Opportunities

**Index Tuning:**
```sql
-- Add covering index for common query
CREATE INDEX idx_agent_files_source_path_sha
ON agent_files(source_id, file_path, content_sha);

-- This allows: SELECT content_sha FROM agent_files WHERE source_id=? AND file_path=?
-- without additional table lookup (index-only scan)
```

**Connection Pooling:**
```python
# Future enhancement: Connection pooling for multi-threaded scenarios
from contextlib import contextmanager
import threading

class AgentSyncState:
    def __init__(self, ...):
        self._connection_pool = []
        self._pool_lock = threading.Lock()

    @contextmanager
    def _get_connection(self):
        """Get connection from pool or create new."""
        with self._pool_lock:
            if self._connection_pool:
                conn = self._connection_pool.pop()
            else:
                conn = sqlite3.connect(self.db_path)
                # Configure connection...

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            with self._pool_lock:
                self._connection_pool.append(conn)
```

**Batch Operations:**
```python
def track_files_batch(self, source_id: str, files: List[Dict[str, Any]]):
    """Track multiple files in single transaction."""
    with self._get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO agent_files (source_id, file_path, content_sha, local_path, synced_at, file_size)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id, file_path) DO UPDATE SET
                content_sha = excluded.content_sha,
                synced_at = excluded.synced_at
            """,
            [
                (
                    source_id,
                    f["file_path"],
                    f["content_sha"],
                    f.get("local_path"),
                    datetime.now(timezone.utc).isoformat(),
                    f.get("file_size"),
                )
                for f in files
            ]
        )
```

### 6.3 Scalability Analysis

**Current Scale (Stage 1):**
- Sources: 1-5
- Files per source: 10-20
- Sync frequency: 1-4 times/day
- **Performance:** Excellent (<100ms per sync)

**Expected Scale (Stage 2-3):**
- Sources: 10-50
- Files per source: 50-100
- Sync frequency: 10-20 times/day
- **Performance:** Good (<500ms per sync with indexes)

**Maximum Scale (Theoretical):**
- Sources: 100+
- Files per source: 1000+
- Sync frequency: Continuous (webhook-triggered)
- **Performance:** Requires connection pooling and batch operations

---

## 7. Implementation Risks

### 7.1 Technical Risks

**Risk 1: SQLite File Locking**
- **Severity:** Medium
- **Probability:** Low
- **Impact:** Database locked errors during concurrent access
- **Mitigation:** Use connection-per-operation pattern; retry logic with exponential backoff
- **Fallback:** Implement connection pooling with mutex locks

**Risk 2: Schema Migration Complexity**
- **Severity:** Low
- **Probability:** Medium (future schema changes inevitable)
- **Impact:** Breaking changes for existing databases
- **Mitigation:** Include schema_metadata table with version tracking; implement migration framework
- **Fallback:** Manual migration scripts with clear documentation

**Risk 3: Content Hash Calculation Performance**
- **Severity:** Low
- **Probability:** Low
- **Impact:** Sync operations slow down for large agent files
- **Mitigation:** Use existing `get_file_hash()` utility (chunked reading); SHA-256 is fast (<1ms for 1MB file)
- **Fallback:** Cache hashes in memory during sync

**Risk 4: Database Corruption**
- **Severity:** High
- **Probability:** Very Low
- **Impact:** Loss of sync state; need to re-download all agents
- **Mitigation:** SQLite is robust with ACID guarantees; regular backups via `cleanup_old_history()`
- **Fallback:** Database is cache-like; can be rebuilt from scratch

### 7.2 Integration Risks

**Risk 1: Backward Compatibility with ETagCache**
- **Severity:** Medium
- **Probability:** Medium
- **Impact:** Breaking change for existing installations
- **Mitigation:** Automatic migration from JSON to SQLite; keep old cache as backup
- **Fallback:** Manual migration script with clear instructions

**Risk 2: Multi-Source Coordination**
- **Severity:** Low
- **Probability:** Low
- **Impact:** Conflicts when multiple sources provide same agent
- **Mitigation:** Source ID ensures isolation; version comparison happens at deployment layer (not sync layer)
- **Fallback:** Document source priority in configuration

**Risk 3: Testing Coverage Gaps**
- **Severity:** Medium
- **Probability:** Medium
- **Impact:** Edge cases not caught during testing
- **Mitigation:** Comprehensive unit tests (85%+ coverage target); integration tests with mocked HTTP
- **Fallback:** Canary deployment; gradual rollout

---

## 8. Recommended Implementation Approach

### 8.1 Implementation Phases

**Phase 1: Core Database Service (4-6 hours)**
1. Create `agent_sync_state.py` with AgentSyncState class
2. Implement schema creation and initialization
3. Implement source CRUD operations
4. Implement file tracking operations
5. Implement sync history operations

**Phase 2: GitSourceSyncService Integration (3-4 hours)**
1. Update `git_source_sync_service.py` to use AgentSyncState
2. Replace ETagCache references
3. Add content hash tracking to sync_agents()
4. Add automatic migration from JSON cache
5. Update error handling

**Phase 3: Migration and Testing (4-6 hours)**
1. Write migration script
2. Write comprehensive unit tests (85%+ coverage)
3. Write integration tests
4. Test migration with real ETag cache data
5. Performance profiling and optimization

**Phase 4: Documentation and Deployment (2-3 hours)**
1. Update API documentation
2. Write migration guide for users
3. Update CONTRIBUTING.md with database patterns
4. Create example usage documentation
5. Prepare release notes

**Total Estimated Effort:** 13-19 hours

### 8.2 Success Criteria

**Functional Requirements:**
- ✅ SQLite database created at `~/.config/claude-mpm/agent_sync.db`
- ✅ All three tables (sources, agent_files, sync_history) created with indexes
- ✅ AgentSyncState service provides full CRUD operations
- ✅ Per-file SHA-256 content hash tracking implemented
- ✅ GitSourceSyncService successfully integrated
- ✅ Automatic migration from JSON ETag cache
- ✅ Sync history audit trail maintained

**Non-Functional Requirements:**
- ✅ 85%+ test coverage
- ✅ <100ms database overhead per sync operation
- ✅ No breaking changes for existing installations
- ✅ Comprehensive error handling with graceful degradation
- ✅ Clear documentation and migration guides

**Quality Gates:**
- ✅ All unit tests passing
- ✅ All integration tests passing
- ✅ No regressions in existing sync functionality
- ✅ Performance benchmarks met (<100ms overhead)
- ✅ Code review approved
- ✅ Documentation complete

---

## 9. Open Questions and Future Work

### 9.1 Open Questions

**Q1: Should we track commit SHAs at source level or file level?**
- **Current Design:** Source level (`sources.last_sha`)
- **Alternative:** File level (add `commit_sha` to `agent_files`)
- **Recommendation:** Source level for Stage 1; file level requires GitHub API integration (future ticket 1M-390)

**Q2: How should we handle multiple sources providing same agent?**
- **Current Design:** Source isolation via `source_id`; deployment layer handles version comparison
- **Recommendation:** Document in configuration that highest version wins (existing behavior)

**Q3: Should we implement automatic database backups?**
- **Current Design:** No automatic backups; database is cache-like
- **Recommendation:** Not needed for Stage 1; database can be rebuilt from remote sources

**Q4: How to handle schema migrations in future?**
- **Current Design:** Schema version tracked in `schema_metadata`
- **Recommendation:** Implement migration framework in future ticket when first schema change needed

### 9.2 Future Enhancements

**Enhancement 1: Async Database Operations**
- **Description:** Use `aiosqlite` for async/await pattern
- **Benefit:** Better integration with async sync operations
- **Effort:** 4-6 hours
- **Priority:** Low (current sync is sequential anyway)

**Enhancement 2: Database Vacuum and Optimization**
- **Description:** Periodic `VACUUM` to reclaim space, `ANALYZE` for query optimization
- **Benefit:** Maintain performance as database grows
- **Effort:** 2-3 hours
- **Priority:** Medium (implement when database >1MB)

**Enhancement 3: Webhook-Triggered Sync**
- **Description:** GitHub webhook integration for instant updates
- **Benefit:** Sub-second sync latency vs. polling
- **Effort:** 8-12 hours
- **Priority:** Medium (blocks real-time agent updates)

**Enhancement 4: Multi-Repository Support**
- **Description:** Track files from multiple Git repositories
- **Benefit:** Community agent marketplace
- **Effort:** 6-8 hours (mostly configuration and UI)
- **Priority:** High (ticket 1M-390 depends on this)

**Enhancement 5: Sync Analytics Dashboard**
- **Description:** Web UI showing sync history, file changes, performance metrics
- **Benefit:** Better observability and debugging
- **Effort:** 12-16 hours
- **Priority:** Low (nice-to-have)

---

## 10. File Locations Summary

**New Files:**
```
/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/
├── agent_sync_state.py                    # NEW: AgentSyncState service (~500 lines)

/Users/masa/Projects/claude-mpm/scripts/
├── migrate_etag_cache_to_sqlite.py        # NEW: Migration script (~100 lines)

/Users/masa/Projects/claude-mpm/tests/services/agents/sources/
├── test_agent_sync_state.py               # NEW: Unit tests (~800 lines)
└── test_git_source_sync_integration.py    # NEW: Integration tests (~300 lines)
```

**Modified Files:**
```
/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/
├── git_source_sync_service.py             # MODIFIED: Replace ETagCache (~150 lines changed)
└── __init__.py                            # MODIFIED: Export AgentSyncState (~2 lines)
```

**Database File (Runtime):**
```
~/.config/claude-mpm/
└── agent_sync.db                          # SQLite database (~50KB)
```

---

## 11. Related Tickets and Dependencies

**Parent Issue:**
- 1M-382: Multi-source agent management system

**Depends On:**
- None (self-contained implementation)

**Blocks:**
- 1M-390: Multi-repository agent sync (needs state tracking for multiple sources)
- Future: Webhook-triggered sync (needs change detection via content hashes)

**Related Tickets:**
- 1M-387: GitSourceSyncService with ETag-based caching (COMPLETED - foundation for this work)

---

## 12. Conclusion

This research provides a comprehensive technical specification for implementing SQLite-based state tracking for agent sync operations. The proposed design:

✅ **Meets all acceptance criteria** from ticket 1M-388
✅ **Follows existing service patterns** (ConfigServiceBase, LifecycleServiceBase)
✅ **Provides clear integration path** with GitSourceSyncService
✅ **Includes comprehensive testing strategy** (85%+ coverage target)
✅ **Addresses implementation risks** with mitigation strategies
✅ **Enables future enhancements** (multi-source, webhooks, analytics)

**Recommended Next Steps:**
1. Review and approve this technical specification
2. Create implementation tasks from Phase 1-4 breakdown
3. Begin Phase 1: Core Database Service implementation
4. Validate with unit tests before integration
5. Complete integration and migration in Phases 2-3
6. Document and deploy in Phase 4

**Estimated Timeline:** 2-3 days for complete implementation and testing

---

**End of Research Document**
