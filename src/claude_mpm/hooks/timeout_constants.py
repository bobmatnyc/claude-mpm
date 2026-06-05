"""
Canonical hook timeout constants for Claude MPM.

WHAT: Defines the authoritative timeout values for all Claude Code hook events
      and exposes a helper function to look up the canonical timeout by event name.

WHY: Three independent files (hooks/claude_hooks/installer.py,
     services/hook_installer_service.py, and
     migrations/migrate_dedup_hook_registrations.py) each maintained their own
     copy of these constants, which is exactly the drift that caused issue #677
     (duplicate hook registrations with mismatched timeouts).  A single shared
     module eliminates that class of bug.

References
----------
SPEC-HOOKS-04~1 : docs/specs/hooks.md#SPEC-HOOKS-04~1
"""

# ---------------------------------------------------------------------------
# Single source of truth for hook timeouts.
#
# Most events: 15 s — the hook returns async immediately so a short timeout
# is appropriate.
#
# Long-running cleanup events: 60 s — StopFailure, SessionEnd and PostCompact
# may perform disk I/O (session state flush, compaction) that legitimately
# takes longer.
# ---------------------------------------------------------------------------

DEFAULT_HOOK_TIMEOUT: int = 15

CANONICAL_HOOK_TIMEOUTS: dict[str, int] = {
    "StopFailure": 60,
    "SessionEnd": 60,
    "PostCompact": 60,
}


def canonical_timeout(event: str) -> int:
    """Return the canonical timeout (seconds) for the given hook event.

    WHAT: Looks up ``event`` in ``CANONICAL_HOOK_TIMEOUTS``; falls back to
          ``DEFAULT_HOOK_TIMEOUT`` (15 s) for events not in the map.

    WHY: Centralises the lookup so callers never inline their own default and
         can never diverge from the shared map.

    Args:
        event: The Claude Code hook event name (e.g. ``"PreToolUse"``).

    Returns:
        Integer timeout in seconds.
    """
    return CANONICAL_HOOK_TIMEOUTS.get(event, DEFAULT_HOOK_TIMEOUT)
