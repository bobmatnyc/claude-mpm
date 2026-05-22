"""User choices persistence for migration skills.

Tracks user decisions about optional migration skill wizards (install, defer,
decline, complete) in ``~/.claude-mpm/user-choices.json``. Used by the migration
skill infrastructure to determine which optional setup wizards should be
surfaced to the PM agent.

State file schema::

    {
      "migration_skills": {
        "trusty-services": {
          "status": "declined" | "deferred" | "completed" | "pending",
          "timestamp": "2026-05-21T17:00:00",
          "deferred_until": "2026-05-22T17:00:00",  # optional
          "reason": "user said: not now"            # optional
        }
      }
    }

The module never raises on I/O errors — corrupted JSON or missing files are
silently treated as empty state. This is intentional: user-choice tracking is
advisory, not load-bearing, and must not break startup migrations.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default state file location. Overridable via constructor for testing.
_DEFAULT_STATE_FILE = Path.home() / ".claude-mpm" / "user-choices.json"


# Valid status values
STATUS_PENDING = "pending"
STATUS_DEFERRED = "deferred"
STATUS_DECLINED = "declined"
STATUS_COMPLETED = "completed"

_VALID_STATUSES = frozenset(
    {STATUS_PENDING, STATUS_DEFERRED, STATUS_DECLINED, STATUS_COMPLETED}
)


class UserChoicesManager:
    """Manage persistent user choices for migration skills.

    All operations are best-effort: corrupted state is treated as empty, and
    write failures are logged but never raised. Callers should never depend on
    this manager for correctness of the underlying system.
    """

    def __init__(self, state_file: Path | None = None) -> None:
        """Initialize manager with optional custom state file path.

        Args:
            state_file: Path to JSON state file. Defaults to
                ``~/.claude-mpm/user-choices.json``.
        """
        self.state_file = state_file if state_file is not None else _DEFAULT_STATE_FILE

    def _load(self) -> dict[str, Any]:
        """Load state from disk, returning empty state on any error."""
        if not self.state_file.exists():
            return {"migration_skills": {}}

        try:
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning(
                    "user-choices.json root is not a dict; treating as empty"
                )
                return {"migration_skills": {}}
            if "migration_skills" not in data or not isinstance(
                data["migration_skills"], dict
            ):
                data["migration_skills"] = {}
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Failed to load user-choices.json (%s); treating as empty", exc
            )
            return {"migration_skills": {}}

    def _save(self, state: dict[str, Any]) -> None:
        """Persist state to disk, logging but not raising on failure."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except OSError as exc:
            logger.warning("Failed to save user-choices.json: %s", exc)

    def get_choice(self, skill_key: str) -> dict[str, Any] | None:
        """Return the recorded choice for ``skill_key``, or None if absent."""
        state = self._load()
        entry = state.get("migration_skills", {}).get(skill_key)
        if not isinstance(entry, dict):
            return None
        return entry

    def set_choice(
        self,
        skill_key: str,
        status: str,
        reason: str = "",
        deferred_until: str | None = None,
    ) -> None:
        """Record a choice for ``skill_key``.

        Args:
            skill_key: Migration skill identifier (e.g., ``"trusty-services"``).
            status: One of pending/deferred/declined/completed.
            reason: Optional human-readable note (e.g., user's words).
            deferred_until: ISO 8601 timestamp; only used when status is deferred.
        """
        if status not in _VALID_STATUSES:
            logger.warning(
                "Ignoring invalid status %r for %s (valid: %s)",
                status,
                skill_key,
                sorted(_VALID_STATUSES),
            )
            return

        state = self._load()
        skills = state.setdefault("migration_skills", {})

        entry: dict[str, Any] = {
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        if reason:
            entry["reason"] = reason
        if deferred_until and status == STATUS_DEFERRED:
            entry["deferred_until"] = deferred_until

        skills[skill_key] = entry
        self._save(state)

    def is_pending(self, skill_key: str) -> bool:
        """Return True if ``skill_key`` should be surfaced to the user now.

        A skill is pending when:
          * No choice has been recorded yet, OR
          * The recorded status is ``pending``, OR
          * The recorded status is ``deferred`` and ``deferred_until`` has passed.

        ``declined`` and ``completed`` skills are never pending.
        """
        entry = self.get_choice(skill_key)
        if entry is None:
            return True

        status = entry.get("status")
        if status in (STATUS_DECLINED, STATUS_COMPLETED):
            return False
        if status == STATUS_PENDING:
            return True
        if status == STATUS_DEFERRED:
            deferred_until = entry.get("deferred_until")
            if not deferred_until:
                # Malformed defer entry; treat as pending so user sees it again.
                return True
            try:
                until = datetime.fromisoformat(deferred_until)
            except ValueError:
                return True
            return datetime.now(UTC) >= until

        # Unknown status — be conservative and surface it.
        return True

    def decline(self, skill_key: str, reason: str = "") -> None:
        """Mark ``skill_key`` as permanently declined."""
        self.set_choice(skill_key, STATUS_DECLINED, reason=reason)

    def defer(self, skill_key: str, hours: int = 24, reason: str = "") -> None:
        """Defer ``skill_key`` for ``hours`` hours.

        After the deferral expires, ``is_pending()`` returns True again.
        """
        deferred_until = (datetime.now(UTC) + timedelta(hours=hours)).isoformat(
            timespec="seconds"
        )
        self.set_choice(
            skill_key,
            STATUS_DEFERRED,
            reason=reason,
            deferred_until=deferred_until,
        )

    def complete(self, skill_key: str, reason: str = "") -> None:
        """Mark ``skill_key`` as completed (installation successful)."""
        self.set_choice(skill_key, STATUS_COMPLETED, reason=reason)

    def get_all_pending(self, known_keys: list[str] | None = None) -> list[str]:
        """Return list of skill keys whose status is pending.

        Args:
            known_keys: Optional list of skill keys to check. When provided,
                returns the subset that is pending (including keys that have no
                recorded choice). When ``None``, only returns keys that have an
                explicit pending/expired-defer entry in the state file.
        """
        if known_keys is not None:
            return [k for k in known_keys if self.is_pending(k)]

        state = self._load()
        return [
            key
            for key, entry in state.get("migration_skills", {}).items()
            if isinstance(entry, dict) and self.is_pending(key)
        ]
