"""
Shared hook-identity predicate for Claude MPM.

WHAT: Exports ``is_our_hook(hook)`` — a single function that both hook
      installers (HookInstaller and HookInstallerService) call to decide
      whether a hook command dict belongs to claude-mpm.

WHY: ``installer.py`` and ``hook_installer_service.py`` each had their own
     ``_is_our_hook`` whose legacy substring sets diverged, so one installer
     could fail to recognise hooks written by the other (issue #677 follow-up).
     Consolidating into one module removes the divergence and makes future
     changes to hook recognition a single-line edit.

References
----------
SPEC-HOOKS-04~1 : docs/specs/hooks.md#SPEC-HOOKS-04~1
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Legacy substring constants — union of both previous installer sets so that
# hooks written by either installer before the ``_mpm`` marker was introduced
# are still recognised.
#
# installer.py had:   "claude-hook-fast.sh", "claude-hook-handler.sh",
#                     endswith("claude-mpm-hook.sh"), == "claude-hook"
# service.py had:     "hook_wrapper.sh", "claude-hook-handler.sh",
#                     "claude-mpm" in command, == "claude-hook"
# ---------------------------------------------------------------------------

_LEGACY_MPM_SUBSTRINGS: tuple[str, ...] = (
    "claude-hook-fast.sh",
    "claude-hook-handler.sh",
    "hook_wrapper.sh",
    "claude-mpm",
)

_LEGACY_MPM_EXACT: tuple[str, ...] = ("claude-hook",)

_LEGACY_MPM_SUFFIX: tuple[str, ...] = ("claude-mpm-hook.sh",)


def is_our_hook(hook: dict[str, Any]) -> bool:
    """Return True if a hook command dict belongs to claude-mpm.

    WHAT: Checks the authoritative ``_mpm: True`` marker first; falls back to
          the union of legacy substring/suffix/exact-match rules from both
          ``installer.py`` and ``hook_installer_service.py`` so that hooks
          written by either installer before the marker was introduced are
          still correctly identified.

    WHY: Both installers previously defined diverging ``_is_our_hook``
         functions, which could cause one installer to miss hooks written by
         the other and therefore add duplicate entries (issue #677).

    Args:
        hook: A hook command dict from a Claude Code settings.json hooks block.

    Returns:
        True if this hook belongs to claude-mpm, False otherwise.
    """
    if not isinstance(hook, dict):
        return False
    if hook.get("type") != "command":
        return False

    # Primary: explicit marker is the authoritative signal (written by both
    # installers for all new entries since the _mpm marker was added).
    if hook.get("_mpm"):
        return True

    command = str(hook.get("command", ""))

    # Legacy fallback: exact match.
    if command in _LEGACY_MPM_EXACT:
        return True

    # Legacy fallback: substring match (handles absolute-path script names).
    if any(sub in command for sub in _LEGACY_MPM_SUBSTRINGS):
        return True

    # Legacy fallback: suffix match (handles old deployed hook script name).
    if any(command.endswith(suf) for suf in _LEGACY_MPM_SUFFIX):
        return True

    return False
