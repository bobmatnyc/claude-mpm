"""Maps GitHub Issues/PRs to MPM session names and comment IDs."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_PERSIST_PATH = (
    Path.home() / ".claude-mpm" / "channels" / "github-sessions.json"
)


class GitHubSessionMapper:
    """Maps entity keys like '{owner}/{repo}/issues/{number}' to session names.

    Entity key format:
        "{owner}/{repo}/issues/{number}"  for GitHub Issues
        "{owner}/{repo}/pulls/{number}"   for GitHub PRs

    Persists to disk so that re-triggering is prevented after daemon restarts.
    """

    def __init__(self, persist_path: Path | None = None) -> None:
        self._persist_path = persist_path or _DEFAULT_PERSIST_PATH
        # entity_key -> session_name
        self._map: dict[str, str] = {}
        # entity_key -> comment_id (optional)
        self._comment_map: dict[str, int] = {}
        self.load()

    # ── Persistence ──────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load persisted state from disk. Silently ignores missing or corrupt files."""
        try:
            if self._persist_path.exists():
                raw = json.loads(self._persist_path.read_text())
                self._map = raw.get("sessions", {})
                self._comment_map = {
                    k: int(v) for k, v in raw.get("comments", {}).items()
                }
                logger.debug(
                    "GitHubSessionMapper loaded %d entries from %s",
                    len(self._map),
                    self._persist_path,
                )
        except Exception:
            logger.warning(
                "Failed to load github-sessions.json; starting fresh", exc_info=True
            )
            self._map = {}
            self._comment_map = {}

    def save(self) -> None:
        """Persist current mapping to disk."""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            raw = {
                "sessions": self._map,
                "comments": self._comment_map,
            }
            self._persist_path.write_text(json.dumps(raw, indent=2))
        except Exception:
            logger.warning("Failed to save github-sessions.json", exc_info=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def register(
        self,
        entity_key: str,
        session_name: str,
        comment_id: int | None = None,
    ) -> None:
        """Register an entity key as handled, associating it with a session and optional comment."""
        self._map[entity_key] = session_name
        if comment_id is not None:
            self._comment_map[entity_key] = comment_id
        self.save()

    def get_session_name(self, entity_key: str) -> str | None:
        """Return the session name for an entity key, or None if not registered."""
        return self._map.get(entity_key)

    def get_comment_id(self, entity_key: str) -> int | None:
        """Return the GitHub comment ID for an entity key, or None if not tracked."""
        return self._comment_map.get(entity_key)

    def update_comment_id(self, entity_key: str, comment_id: int) -> None:
        """Update the comment ID for an already-registered entity."""
        if entity_key in self._map:
            self._comment_map[entity_key] = comment_id
            self.save()

    def remove(self, entity_key: str) -> None:
        """Deregister an entity key (called when a session ends)."""
        self._map.pop(entity_key, None)
        self._comment_map.pop(entity_key, None)
        self.save()

    def is_handled(self, entity_key: str) -> bool:
        """Return True if this entity key already has an active session."""
        return entity_key in self._map

    def all_entity_keys(self) -> list[str]:
        """Return all tracked entity keys."""
        return list(self._map.keys())
