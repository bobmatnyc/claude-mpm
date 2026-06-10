"""Shared, console-free trusty hook-injection logic.

Why: both the interactive ``claude-mpm setup trusty-*`` path
(:class:`~claude_mpm.cli.commands.setup.handlers.trusty.TrustyMixin`) and the
startup autodetect migration
(:mod:`claude_mpm.migrations.migrate_trusty_autodetect`) need to inject the same
Claude Code settings hooks (SessionStart/Stop/SubagentStop for trusty-memory,
PostToolUse index for trusty-search). Previously that logic lived inside
``TrustyMixin`` and was coupled to a rich ``console``, so the migration — which
must stay dependency-light and silent — could not reuse it.

What: pure functions that read/merge/atomically-write a Claude Code
``settings.json`` hook block, deduping by ``_mpm_service`` and stripping legacy
predecessor hooks (kuzu-memory / mcp-vector-search). Reporting is delegated to an
optional ``report`` callback so callers choose their own sink (rich console for
setup, ``logging`` for the migration, or ``None`` for total silence).

Test: ``tests/test_trusty_hooks.py`` and ``tests/migrations/test_trusty_autodetect.py``
cover idempotency, legacy-hook stripping, the "project settings only if it
already exists" rule, and parity with the old ``TrustyMixin`` output structure.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_mpm.hooks.hook_identity import is_our_hook

if TYPE_CHECKING:
    from collections.abc import Callable

# Legacy services whose hooks should be removed when injecting trusty hooks.
# These are the predecessors of trusty-search / trusty-memory and would
# duplicate or conflict with the new daemons.
_LEGACY_SERVICES = {"kuzu-memory", "mcp-vector-search"}

# Hook specifications keyed by trusty service name. Each entry lists the
# (event, matcher, hook_dict) tuples to inject. The ``_mpm_service`` tag is
# the dedup key — re-running injection will not duplicate hooks.
_TRUSTY_HOOK_SPECS: dict[str, list[tuple[str, str, dict[str, Any]]]] = {
    "trusty-memory": [
        (
            event,
            "*",
            {
                "type": "command",
                "command": "claude-hook",
                "timeout": 15,
                "_mpm": True,
                "_mpm_service": "trusty-memory",
            },
        )
        for event in ("SessionStart", "Stop", "SubagentStop")
    ],
    "trusty-search": [
        (
            "PostToolUse",
            "Write|MultiEdit|Edit|NotebookEdit",
            {
                "type": "command",
                "command": "python3",
                "args": ["-m", "claude_mpm.hooks.trusty_index_hook"],
                "timeout": 10,
                "async": True,
                "_mpm": True,
                "_mpm_service": "trusty-search",
            },
        ),
    ],
}


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically: write to a sibling temp file, then rename.

    Why: settings.json is read by Claude Code on every hook invocation; a
    partial write would crash hooks until repaired.
    What: dumps ``data`` to a temp file in the same directory, then
    ``os.replace`` (atomic on the same filesystem) over the target.
    Test: covered indirectly by hook-injection tests that re-read the file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        Path(tmp_path).replace(path)
    except Exception:
        # Best effort cleanup of temp file.
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass
        raise


def _load_settings(path: Path) -> dict[str, Any]:
    """Load a Claude Code settings.json, returning a skeleton on absence.

    Why: callers need a dict with a guaranteed ``hooks`` object to merge into,
    whether or not the file already exists.
    What: returns ``{"hooks": {}}`` when absent; otherwise parses the file and
    ensures a dict ``hooks`` key exists. Raises :class:`RuntimeError` on a
    malformed file so the caller can skip it without corrupting it.
    Test: ``tests/test_trusty_hooks.py`` exercises absent / valid / malformed.
    """
    if not path.exists():
        return {"hooks": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} root is not a JSON object")
    data.setdefault("hooks", {})
    if not isinstance(data["hooks"], dict):
        raise RuntimeError(f"{path}: 'hooks' is not an object")
    return data


def _strip_legacy_hooks(hooks_root: dict[str, Any]) -> int:
    """Remove legacy-service hooks across all events, in place.

    Why: trusty-memory / trusty-search supersede kuzu-memory / mcp-vector-search;
    leaving the predecessors wired up duplicates or conflicts with the new ones.
    What: drops any hook tagged ``_mpm_service in _LEGACY_SERVICES``, collapses
    now-empty groups, and deletes now-empty event lists. Returns the count of
    removed hooks.
    Test: ``tests/test_trusty_hooks.py::test_strips_legacy_hooks``.
    """
    removed_count = 0
    for event_name, groups in list(hooks_root.items()):
        if not isinstance(groups, list):
            continue
        new_groups: list[dict[str, Any]] = []
        for group in groups:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            inner = group.get("hooks")
            if not isinstance(inner, list):
                new_groups.append(group)
                continue
            filtered_inner = [
                h
                for h in inner
                if not (
                    isinstance(h, dict) and h.get("_mpm_service") in _LEGACY_SERVICES
                )
            ]
            dropped = len(inner) - len(filtered_inner)
            if dropped:
                removed_count += dropped
            # Keep the group if it still has hooks, or if it was already empty
            # (we only drop groups that became empty as a result of removal).
            if filtered_inner:
                group["hooks"] = filtered_inner
                new_groups.append(group)
            elif not inner:
                new_groups.append(group)
            # else: group emptied by removal — drop it.
        if new_groups:
            hooks_root[event_name] = new_groups
        else:
            del hooks_root[event_name]
    return removed_count


def inject_hooks_to_settings(
    settings_path: Path,
    services: list[str],
    report: Callable[[str], None] | None = None,
) -> bool:
    """Inject trusty hook entries into a Claude Code settings.json.

    Why: centralizes the merge so the interactive setup command and the startup
    migration produce byte-identical hook structures from one implementation.
    What: for each requested service, strips legacy-service hooks across all
    events, then adds the hooks declared in ``_TRUSTY_HOOK_SPECS[service]`` to
    the matching ``(event, matcher)`` group, skipping any whose ``_mpm_service``
    already exists in that group (idempotent). Creates the file with
    ``{"hooks": {}}`` if missing, preserves unrelated hooks, and writes
    atomically. ``report`` (if given) receives human-readable status lines.
    Returns ``True`` if the file was changed (removals or additions), else
    ``False``.
    Test: ``tests/test_trusty_hooks.py`` (idempotency, legacy strip, parity) and
    ``tests/migrations/test_trusty_autodetect.py``.
    """

    def _say(msg: str) -> None:
        if report is not None:
            report(msg)

    try:
        settings = _load_settings(settings_path)
    except RuntimeError as exc:
        _say(f"⚠ Skipping {settings_path}: {exc}")
        return False

    hooks_root: dict[str, Any] = settings["hooks"]
    added: list[str] = []
    merged: list[str] = []
    skipped: list[str] = []

    # ----- Removal pass: drop legacy-service hooks across all events.
    removed_count = _strip_legacy_hooks(hooks_root)

    # ----- Injection pass: add trusty hooks idempotently.
    for service in services:
        for event, matcher, hook_def in _TRUSTY_HOOK_SPECS.get(service, []):
            groups = hooks_root.setdefault(event, [])
            if not isinstance(groups, list):
                _say(
                    f"⚠ {settings_path}: '{event}' is not a list — skipping injection."
                )
                continue

            tag = hook_def.get("_mpm_service")
            cmd = hook_def.get("command")
            hook_args = hook_def.get("args") or []

            # ----- Cross-matcher-group duplicate scan -----
            # Before appending, scan ALL groups for this event — not just the
            # target matcher group.  A hook is a duplicate if EITHER:
            #   (a) it carries the same _mpm_service tag, OR
            #   (b) it is one of our hooks (is_our_hook) invoking the same
            #       command+args (i.e. a bare MPM hook written by HookInstaller
            #       that lacks the _mpm_service tag but is functionally identical).
            # When a bare MPM hook matching (b) is found, merge the _mpm_service
            # tag onto it so future runs recognise it as a duplicate via path (a).
            duplicate_found = False
            for group in groups:
                if not isinstance(group, dict):
                    continue
                inner: list[Any] = (
                    group.get("hooks") if isinstance(group.get("hooks"), list) else []
                )  # type: ignore[assignment]
                for h in inner:
                    if not isinstance(h, dict):
                        continue
                    # Path (a): tagged duplicate (same _mpm_service).
                    if tag and h.get("_mpm_service") == tag:
                        duplicate_found = True
                        break
                    # Path (b): bare MPM hook with same command+args fingerprint.
                    if (
                        is_our_hook(h)
                        and h.get("command") == cmd
                        # Order-sensitive list equality is correct here: MPM hook
                        # definitions use fixed argument ordering, so two entries
                        # with the same args in the same order are the same hook.
                        and (h.get("args") or []) == hook_args
                    ):
                        # Merge tag so the next run uses path (a) directly.
                        if tag:
                            # Deliberate in-place mutation: `h` is a reference into
                            # the live `settings` dict, so this write is captured by
                            # the `changed`/`merged` write-back path below.
                            h["_mpm_service"] = tag
                            merged.append(f"{event}[{group.get('matcher', '*')}]:{tag}")
                        duplicate_found = True
                        break
                if duplicate_found:
                    break

            if duplicate_found:
                skipped.append(f"{event}[{matcher}]:{tag or '<untagged>'}")
                continue

            # No duplicate found anywhere — append to the target matcher group.
            target_group: dict[str, Any] | None = None
            for group in groups:
                if (
                    isinstance(group, dict)
                    and group.get("matcher") == matcher
                    and isinstance(group.get("hooks"), list)
                ):
                    target_group = group
                    break
            if target_group is None:
                target_group = {"matcher": matcher, "hooks": []}
                groups.append(target_group)

            target_group["hooks"].append(hook_def)
            added.append(f"{event}[{matcher}]:{tag}")

    changed = bool(removed_count or added or merged)

    # ----- Write back atomically (only when something actually changed).
    if changed:
        try:
            _atomic_write_json(settings_path, settings)
        except OSError as exc:
            _say(f"✗ Failed to write {settings_path}: {exc}")
            return False

    # ----- Report.
    rel = str(settings_path)
    if removed_count:
        _say(
            f"• {rel}: removed {removed_count} legacy hook(s) "
            f"({', '.join(sorted(_LEGACY_SERVICES))})"
        )
    if added:
        _say(f"✓ {rel}: added {len(added)} hook(s): {', '.join(added)}")
    if merged:
        _say(
            f"✓ {rel}: merged _mpm_service tag onto {len(merged)} bare hook(s): {', '.join(merged)}"
        )
    if skipped:
        _say(f"• {rel}: {len(skipped)} hook(s) already present, skipped")
    if not (removed_count or added or merged or skipped):
        _say(f"• {rel}: no hook changes needed")

    return changed


def inject_trusty_hooks(
    services: list[str],
    project_dir: Path | None = None,
    report: Callable[[str], None] | None = None,
) -> bool:
    """Inject hooks into both project and user-level Claude Code settings.

    Why: hooks must apply both per-user (the documented setup intent) and
    per-project (when a project already opts into shared settings), without
    silently creating a project-level config a user never asked for.
    What: injects into ``<project_dir>/.claude/settings.json`` **only if that
    file already exists**, and always into ``~/.claude/settings.json`` (creating
    it if missing). Returns ``True`` if either file changed.
    Test: ``tests/test_trusty_hooks.py`` verifies the project file is untouched
    when absent and the user file is created/updated.
    """
    project_dir = project_dir or Path.cwd()
    project_settings = project_dir / ".claude" / "settings.json"
    user_settings = Path.home() / ".claude" / "settings.json"

    changed = False
    if project_settings.exists():
        changed |= inject_hooks_to_settings(project_settings, services, report)
    elif report is not None:
        report(
            f"• {project_settings} not found — skipping project-level hook injection."
        )

    # Always inject into user settings (create if missing).
    changed |= inject_hooks_to_settings(user_settings, services, report)
    return changed
