"""CLI interface for recording user migration skill choices.

Allows shell scripts to record/inspect migration skill user choices without
having to import Python directly. Wraps :class:`UserChoicesManager` with a
small, scripted argument surface.

Usage::

    python3 -m claude_mpm.migrations.user_choices_cli <state_key> <action> [reason]

Actions:
    complete    Mark as successfully installed
    decline     Permanently decline (stop asking)
    defer       Defer for 24 hours
    status      Print current status (pending/declined/completed/deferred)
    reset       Reset to pending (clears any recorded choice; for testing)

Examples::

    python3 -m claude_mpm.migrations.user_choices_cli trusty-services complete
    python3 -m claude_mpm.migrations.user_choices_cli trusty-services defer "not now"
    python3 -m claude_mpm.migrations.user_choices_cli trusty-services status

Exit codes:
    0  on success
    1  on usage error or unknown action
    2  on internal failure
"""

from __future__ import annotations

import sys

from .user_choices import (
    STATUS_COMPLETED,
    STATUS_DECLINED,
    STATUS_DEFERRED,
    STATUS_PENDING,
    UserChoicesManager,
)

_USAGE = (
    "Usage: python3 -m claude_mpm.migrations.user_choices_cli "
    "<state_key> <complete|decline|defer|status|reset> [reason]"
)

_VALID_ACTIONS = frozenset({"complete", "decline", "defer", "status", "reset"})


def _print_status(manager: UserChoicesManager, state_key: str) -> int:
    entry = manager.get_choice(state_key)
    if entry is None:
        print(STATUS_PENDING)
        return 0
    status = entry.get("status", STATUS_PENDING)
    print(status)
    return 0


def _reset(manager: UserChoicesManager, state_key: str) -> int:
    """Reset a skill's choice by removing its entry from the state file."""
    # Direct manipulation of internal state; this is testing-only behaviour.
    state = manager._load()
    skills = state.get("migration_skills", {})
    if state_key in skills:
        del skills[state_key]
        manager._save(state)
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)

    if len(args) < 2:
        print(_USAGE, file=sys.stderr)
        return 1

    state_key, action = args[0], args[1]
    reason = " ".join(args[2:]) if len(args) > 2 else ""

    if not state_key or not state_key.strip():
        print("error: state_key must be non-empty", file=sys.stderr)
        return 1

    if action not in _VALID_ACTIONS:
        print(
            f"error: unknown action {action!r}; valid: {sorted(_VALID_ACTIONS)}",
            file=sys.stderr,
        )
        return 1

    manager = UserChoicesManager()

    try:
        if action == "complete":
            manager.complete(state_key, reason=reason or "completed via CLI")
            print(STATUS_COMPLETED)
            return 0
        if action == "decline":
            manager.decline(state_key, reason=reason or "declined via CLI")
            print(STATUS_DECLINED)
            return 0
        if action == "defer":
            manager.defer(state_key, hours=24, reason=reason or "deferred via CLI")
            print(STATUS_DEFERRED)
            return 0
        if action == "status":
            return _print_status(manager, state_key)
        if action == "reset":
            return _reset(manager, state_key)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 1  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
