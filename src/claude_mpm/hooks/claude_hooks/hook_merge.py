"""Shared hook-merge helper used by both HookInstaller and HookInstallerService.

WHAT: Exports ``merge_hooks_for_event`` — a standalone two-pass deduplication
      function that reconciles MPM hook entries in a Claude Code settings block
      and guarantees exactly one MPM hook entry per event after every call.

WHY: The same two-pass dedup algorithm was duplicated verbatim in
     ``HookInstaller._update_claude_settings`` (installer.py) and
     ``HookInstallerService.install_hooks`` (hook_installer_service.py).
     Keeping two copies creates divergence risk: a bug fix or timeout change
     applied to one site can easily be missed in the other, reproducing the
     class of drift that caused issue #677.  A single shared module eliminates
     that risk and makes future changes a single-line edit.

References
----------
SPEC-HOOKS-04~1 : docs/specs/hooks.md#SPEC-HOOKS-04~1
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import logging
    from collections.abc import Callable


def merge_hooks_for_event(
    existing_hooks: list,
    new_hook_command: dict,
    is_our_hook: Callable[[dict], bool],
    logger: logging.Logger,
    use_matcher: bool = True,
) -> list:
    """Merge new_hook_command into existing_hooks, deduplicating MPM entries.

    WHAT: Two-pass idempotent merge that guarantees exactly one MPM hook entry
          per event block regardless of how many times the installer has run.

    WHY: Both HookInstaller and HookInstallerService need identical dedup
         semantics.  Sharing a single implementation prevents the two sites
         from drifting (the root cause of issue #677 follow-up bugs).

    Two-pass algorithm:

    - Pass 1: find the first MPM hook (via ``is_our_hook``), reconcile it to
      canonical values (command, timeout, _mpm), store object identity via
      ``id(hook)`` so Pass 2 can skip it safely even if block/hook indices
      shift due to future list mutations.

    - Pass 2: purge every OTHER MPM hook entry so that re-running the
      installer any number of times converges to exactly one MPM hook per
      event.  User-owned hooks (not recognised by ``is_our_hook``) are never
      touched.

    When no MPM hook exists, appends ``new_hook_command`` to the first block
    whose ``matcher`` satisfies the ``use_matcher`` policy, or creates a new
    block if none exists.

    Args:
        existing_hooks: Current hooks config list for an event type.
        new_hook_command: The canonical MPM hook dict to add/reconcile.
            Must contain at minimum ``"command"``, ``"timeout"``, and
            ``"_mpm": True``.
        is_our_hook: Predicate that returns True for MPM-owned hook dicts.
            Typically ``claude_mpm.hooks.hook_identity.is_our_hook``.
        logger: Logger for debug messages.
        use_matcher: When True (default), the append path looks for a block
            with ``matcher == "*"`` and creates one if missing.  When False,
            the append path looks for a block with no ``matcher`` key and
            creates one without a matcher.  Has no effect when an existing
            MPM hook is found in Pass 1 (the reconcile-then-dedup path).

    Returns:
        Updated hooks list with exactly one MPM hook entry, duplicates removed.
        The same list object is returned (mutated in-place).
    """
    # ------------------------------------------------------------------
    # Pass 1: find the first MPM hook and reconcile it to canonical values.
    #
    # We store the Python object identity (id) of the found hook rather than
    # its (block_idx, hook_idx) coordinates.  Object identity is more robust:
    # if list mutations ever shift indices between Pass 1 and Pass 2, the id
    # still uniquely identifies the one hook we want to keep.
    # ------------------------------------------------------------------
    canonical_hook_id: int | None = None

    for hook_config in existing_hooks:
        if "hooks" in hook_config and isinstance(hook_config["hooks"], list):
            for hook in hook_config["hooks"]:
                if is_our_hook(hook):
                    # Reconcile the FULL entry (command + timeout + _mpm) to the
                    # canonical desired value — not just command.  This prevents
                    # a stale timeout from persisting after an upgrade (issue #677).
                    hook["command"] = new_hook_command["command"]
                    hook["timeout"] = new_hook_command["timeout"]
                    hook["_mpm"] = True
                    canonical_hook_id = id(hook)
                    break
        if canonical_hook_id is not None:
            break

    if canonical_hook_id is not None:
        # ------------------------------------------------------------------
        # Pass 2: purge every OTHER MPM hook entry so that re-running the
        # installer any number of times converges to exactly one entry.
        # We iterate all blocks and filter out MPM entries whose object id
        # does not match the canonical hook we just reconciled above.
        # ------------------------------------------------------------------
        for hook_config in existing_hooks:
            if "hooks" not in hook_config or not isinstance(hook_config["hooks"], list):
                continue
            kept: list = []
            for hook in hook_config["hooks"]:
                if is_our_hook(hook) and id(hook) != canonical_hook_id:
                    # Extra duplicate — drop it.
                    logger.debug("Removing duplicate MPM hook: %s", hook.get("command"))
                else:
                    kept.append(hook)
            hook_config["hooks"] = kept
        return existing_hooks

    # ------------------------------------------------------------------
    # No MPM hook found — append new_hook_command to an appropriate block,
    # or create a new block if none exists.
    # ------------------------------------------------------------------
    added = False

    for hook_config in existing_hooks:
        matcher = hook_config.get("matcher")
        # Accept a block when:
        #  - use_matcher=True  → block has matcher == "*"
        #  - use_matcher=False → block has matcher == "*" OR no matcher key
        #    (simple events like Stop have no matcher, but if a wildcard block
        #    happens to exist we can reuse it rather than creating a new one)
        if matcher == "*" or (not use_matcher and matcher is None):
            if "hooks" not in hook_config:
                hook_config["hooks"] = []
            hook_config["hooks"].append(new_hook_command)
            added = True
            break

    if not added:
        # No suitable block found — create a new one.
        if use_matcher:
            new_config: dict = {"matcher": "*", "hooks": [new_hook_command]}
        else:
            new_config = {"hooks": [new_hook_command]}
        existing_hooks.append(new_config)

    return existing_hooks
