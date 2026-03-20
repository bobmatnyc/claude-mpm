"""SQLite-backed manifest cache for offline validation and audit trail."""

import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default cache database path
DEFAULT_CACHE_DB = Path.home() / ".claude-mpm" / "cache" / "manifest_cache.db"


class ManifestCache:
    """SQLite-backed cache for agent repository manifests.

    Enables:
    - Offline validation using last-known manifest
    - Audit trail of manifest changes over time
    - Faster startup (skip re-fetch within TTL)

    Example::

        cache = ManifestCache(db_path=tmp_path / "test.db")
        cache.store(
            source_id="my-repo",
            repo_format_version=1,
            min_cli_version="5.10.0",
        )
        entry = cache.get("my-repo")
        assert entry["min_cli_version"] == "5.10.0"
    """

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or DEFAULT_CACHE_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with busy_timeout for concurrent access."""
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self) -> None:
        """Initialize the manifest_cache table."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS manifest_cache (
                    source_id TEXT PRIMARY KEY,
                    repo_format_version INTEGER NOT NULL,
                    min_cli_version TEXT NOT NULL,
                    max_cli_version TEXT,
                    compatibility_ranges TEXT,
                    agent_overrides TEXT,
                    last_checked TIMESTAMP NOT NULL,
                    raw_content TEXT
                )
            """)
            conn.commit()

    def store(
        self,
        source_id: str,
        repo_format_version: int,
        min_cli_version: str,
        max_cli_version: str | None = None,
        compatibility_ranges: list[dict[str, Any]] | None = None,
        agent_overrides: dict[str, Any] | None = None,
        raw_content: str | None = None,
    ) -> None:
        """Store or update a manifest cache entry.

        Args:
            source_id: Unique identifier for the agent source (e.g. repo URL).
            repo_format_version: Integer format version from the manifest.
            min_cli_version: Minimum CLI version string from the manifest.
            max_cli_version: Optional maximum CLI version string.
            compatibility_ranges: Optional list of range dicts.
            agent_overrides: Optional dict of per-agent override dicts.
            raw_content: Optional raw YAML text of the manifest.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO manifest_cache
                (source_id, repo_format_version, min_cli_version, max_cli_version,
                 compatibility_ranges, agent_overrides, last_checked, raw_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    repo_format_version,
                    min_cli_version,
                    max_cli_version,
                    json.dumps(compatibility_ranges) if compatibility_ranges else None,
                    json.dumps(agent_overrides) if agent_overrides else None,
                    datetime.now(UTC).isoformat(),
                    raw_content,
                ),
            )
            conn.commit()

    def get(self, source_id: str) -> dict[str, Any] | None:
        """Retrieve cached manifest data for a source.

        Args:
            source_id: The source identifier to look up.

        Returns:
            A dict with all cache columns, or None if not found.
            JSON columns (compatibility_ranges, agent_overrides) are
            deserialized to Python objects.
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM manifest_cache WHERE source_id = ?",
                (source_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            result = dict(row)
            # Deserialize JSON fields
            if result.get("compatibility_ranges"):
                result["compatibility_ranges"] = json.loads(
                    result["compatibility_ranges"]
                )
            if result.get("agent_overrides"):
                result["agent_overrides"] = json.loads(result["agent_overrides"])
            return result

    def get_all(self) -> list[dict[str, Any]]:
        """Retrieve all cached manifests, ordered by last_checked descending.

        Returns:
            List of dicts, each with all cache columns.  JSON columns are
            deserialized to Python objects.
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM manifest_cache ORDER BY last_checked DESC"
            )
            results = []
            for row in cursor.fetchall():
                entry = dict(row)
                if entry.get("compatibility_ranges"):
                    entry["compatibility_ranges"] = json.loads(
                        entry["compatibility_ranges"]
                    )
                if entry.get("agent_overrides"):
                    entry["agent_overrides"] = json.loads(entry["agent_overrides"])
                results.append(entry)
            return results

    def delete(self, source_id: str) -> bool:
        """Remove a cached manifest entry.

        Args:
            source_id: The source identifier to remove.

        Returns:
            True if an entry was deleted, False if it did not exist.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM manifest_cache WHERE source_id = ?",
                (source_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear(self) -> int:
        """Remove all cached entries.

        Returns:
            Count of deleted entries.
        """
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM manifest_cache")
            conn.commit()
            return cursor.rowcount
