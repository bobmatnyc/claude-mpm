"""Detect pending migration skills on startup.

Scans known skill directories for SKILL.md files with ``type: migration``
frontmatter, cross-references user choices, and writes a notification file at
``~/.claude-mpm/pending-migrations.json`` listing any pending migration skill
wizards. The PM agent reads this list (via :mod:`SkillManager`) to surface
recommendations in its system prompt.

Design constraints (mirrors :mod:`migrate_trusty_autodetect`):

* **Idempotent**: writing the same pending list twice is a no-op.
* **Silent on absence**: missing skill dirs are normal during development.
* **Cheap**: only parses YAML frontmatter, no full skill body load.
* **Never raises**: wrap everything; return ``True`` if state file was written
  successfully, ``False`` only on unrecoverable I/O errors.

Auto-completion: when a migration skill defines ``check_commands`` (shell
commands that verify the service is already installed) and ALL of them succeed,
we automatically mark the skill as completed in user-choices, preventing the PM
from re-suggesting an already-installed service.
"""

from __future__ import annotations

import json
import logging
import shlex
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .user_choices import UserChoicesManager

logger = logging.getLogger(__name__)

# Output file consumed by SkillManager when building PM context.
_PENDING_FILE = Path.home() / ".claude-mpm" / "pending-migrations.json"


# Locations to scan for migration skill definitions. Project-level skills take
# precedence over user-level (handled by skill_manager during context build).
def _skill_search_dirs() -> list[Path]:
    """Return directories that may contain ``<skill>/SKILL.md`` files."""
    return [
        Path.cwd() / ".claude" / "skills",
        Path.home() / ".claude-mpm" / "skills",
        Path.home() / ".claude" / "skills",
    ]


def _parse_migration_skill(skill_file: Path) -> dict[str, Any] | None:
    """Parse a SKILL.md file and return its frontmatter if ``type == "migration"``.

    Returns None if:
      * File can't be read.
      * Frontmatter is missing or malformed.
      * ``type`` field is not ``"migration"``.
    """
    try:
        content = skill_file.read_text(encoding="utf-8")
    except OSError:
        return None

    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        metadata = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        logger.debug("Invalid YAML in %s: %s", skill_file, exc)
        return None

    if not isinstance(metadata, dict):
        return None
    if metadata.get("type") != "migration":
        return None

    return metadata


def _find_migration_skills() -> list[dict[str, Any]]:
    """Discover all migration-type SKILL.md files across search dirs.

    Returns a list of metadata dicts, deduplicated by ``state_key``.
    Project-level entries (first dir in search order) win over user-level.
    """
    found: dict[str, dict[str, Any]] = {}

    for search_dir in _skill_search_dirs():
        if not search_dir.exists() or not search_dir.is_dir():
            continue
        try:
            iterator = search_dir.iterdir()
        except OSError:
            continue

        for skill_dir in iterator:
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            metadata = _parse_migration_skill(skill_file)
            if metadata is None:
                continue

            state_key = metadata.get("state_key") or metadata.get(
                "name", skill_dir.name
            )
            if not isinstance(state_key, str):
                continue

            # First-wins (search dirs are ordered by precedence).
            if state_key in found:
                continue
            found[state_key] = metadata

    return list(found.values())


def _check_commands_pass(check_commands: list[str]) -> bool:
    """Return True if every command in ``check_commands`` exits 0.

    Empty/missing list returns False (can't auto-complete without checks).
    Each command is executed with a 5-second timeout via shell. Any error
    (missing binary, non-zero exit, timeout) yields False.
    """
    if not check_commands:
        return False

    for cmd in check_commands:
        if not isinstance(cmd, str) or not cmd.strip():
            return False
        # If first token is a bare binary like "which trusty-memory", short-circuit
        # via shutil.which to avoid a subprocess when possible. Otherwise fall
        # back to shell invocation.
        tokens = cmd.strip().split()
        if len(tokens) == 2 and tokens[0] == "which":
            if shutil.which(tokens[1]) is None:
                return False
            continue
        try:
            completed = subprocess.run(
                shlex.split(cmd),
                shell=False,
                check=False,
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        if completed.returncode != 0:
            return False

    return True


def _health_checks_pass(health_checks: list[Any]) -> bool:
    """Return True if every URL in ``health_checks`` responds with 2xx.

    ``health_checks`` is a list of dicts shaped like
    ``{"url": "http://...", "service": "..."}``. An empty/missing list
    returns True (no constraint applied). The probe uses a short 3-second
    timeout per URL via :mod:`urllib.request` to avoid adding a network
    dependency.

    Used by startup auto-detection to confirm both binaries are present
    AND daemons are healthy before marking a migration completed.
    """
    if not health_checks:
        return True  # No health checks defined = not constraining

    # Local import to keep module-level import surface small.
    from urllib.error import URLError
    from urllib.request import Request, urlopen

    for entry in health_checks:
        if not isinstance(entry, dict):
            return False
        url = entry.get("url")
        if not isinstance(url, str) or not url.strip():
            return False
        try:
            if not url.startswith(("http://", "https://")):
                return False
            request = Request(url, method="GET")
            with urlopen(request, timeout=3) as response:  # nosec B310 - scheme validated above
                if not (200 <= response.status < 300):
                    return False
        except (URLError, OSError, ValueError):
            return False

    return True


def _write_pending(pending: list[str]) -> bool:
    """Write the pending list to ``_PENDING_FILE``. Returns True on success."""
    try:
        _PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pending": pending,
            "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        with open(_PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return True
    except OSError as exc:
        logger.warning("Failed to write pending-migrations.json: %s", exc)
        return False


def run_migration() -> bool:
    """Detect pending migration skills and update the notification file.

    Returns True if the notification file was written (or there were no
    migration skills to track, which still produces an empty pending list).
    Returns False only when we cannot write the file at all.
    """
    try:
        skills = _find_migration_skills()
        manager = UserChoicesManager()

        pending: list[str] = []
        for skill in skills:
            state_key = skill.get("state_key") or skill.get("name")
            if not isinstance(state_key, str):
                continue

            # Auto-complete if all check_commands AND all health_checks pass
            # and we haven't already recorded a completion. Don't overwrite a
            # declined/deferred entry that the user explicitly set.
            check_commands = skill.get("check_commands")
            health_checks = skill.get("health_checks") or []
            if isinstance(check_commands, list) and check_commands:
                existing = manager.get_choice(state_key)
                already_handled = existing is not None and existing.get("status") in (
                    "completed",
                    "declined",
                    "deferred",
                )
                if (
                    not already_handled
                    and _check_commands_pass(check_commands)
                    and _health_checks_pass(
                        health_checks if isinstance(health_checks, list) else []
                    )
                ):
                    manager.complete(state_key, reason="auto-detected installed")
                    logger.info(
                        "Auto-completed migration skill %s (checks passed)",
                        state_key,
                    )
                    continue

            if manager.is_pending(state_key):
                pending.append(state_key)

        return _write_pending(pending)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("check_migration_skills migration failed unexpectedly: %s", exc)
        return False


def get_pending_state_keys() -> list[str]:
    """Read the current pending list from disk (used by SkillManager).

    Returns an empty list if the file is missing or unreadable.
    """
    if not _PENDING_FILE.exists():
        return []
    try:
        with open(_PENDING_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    pending = data.get("pending") if isinstance(data, dict) else None
    if not isinstance(pending, list):
        return []
    return [p for p in pending if isinstance(p, str)]
