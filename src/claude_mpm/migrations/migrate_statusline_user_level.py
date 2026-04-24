"""
Migration: Move legacy project-level statusline assets to the user level (v6.3.2).

Earlier versions of claude-mpm wrote ``statusline.sh`` and the
``statusLine``/Stop hook entries into ``<project>/.claude/`` on every
``claude-mpm run`` invocation.  That created per-project copies of an
asset that is fundamentally user-global, and meant updates had to be
applied repo-by-repo.

Starting with v6.3.2 the canonical location is ``~/.claude/`` (handled
by ``migrate_statusline_autoconfig`` and ``v6_3_1_deploy_claude_assets``).
This one-shot migration cleans up the legacy project-level remnants in
the *current* project so they don't shadow the user-level copy:

1. If ``<cwd>/.claude/hooks/scripts/statusline.sh`` exists AND carries
   the MPM marker, move it to ``~/.claude/hooks/scripts/statusline.sh``
   (only when the user-level copy is absent — we never overwrite an
   existing user-level script here; that's the autoconfig migration's
   job).  Then remove the project-level file.

2. If ``<cwd>/.claude/settings.json`` has a ``statusLine`` entry whose
   ``command`` references the MPM-managed script (substring match on
   ``statusline.sh``), remove the ``statusLine`` key.

3. Same for the Stop hook: any hook command containing
   ``statusline.sh --clear`` is removed from
   ``<cwd>/.claude/settings.json``.  Empty hook groups and an empty
   ``Stop`` list are pruned to keep settings tidy.

User-customised scripts (no MPM marker) and user-owned settings entries
(``statusLine.command`` pointing somewhere else, Stop hooks unrelated to
statusline) are always left untouched.

Idempotent: re-running the migration on an already-cleaned project is a
no-op.
"""

import json
import logging
import shutil
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

# Marker line that identifies an MPM-managed statusline.sh.
_MPM_MARKER = "# claude-mpm-managed:"

# Substring used to identify an MPM-managed statusLine.command or Stop hook
# command, regardless of whether the path is project-relative or absolute.
_STATUSLINE_COMMAND_MATCH = "statusline.sh"
_STOP_HOOK_MATCH = "statusline.sh --clear"


def _migrate_script(project_claude: Path, user_script: Path) -> bool:
    """Move ``<project>/.claude/hooks/scripts/statusline.sh`` to user level.

    Only acts on MPM-managed copies.  If the user-level destination is
    absent and the project copy carries the MPM marker, the project copy
    is moved up.  Otherwise the project copy is removed (the user-level
    copy is canonical and authoritative).

    Args:
        project_claude: Path to ``<cwd>/.claude``.
        user_script: Path to ``~/.claude/hooks/scripts/statusline.sh``.

    Returns:
        True on success (including no-op), False on error.
    """
    project_script = project_claude / "hooks" / "scripts" / "statusline.sh"
    if not project_script.exists():
        logger.debug(
            "No project-level statusline.sh at %s — nothing to do", project_script
        )
        return True

    try:
        existing = project_script.read_text(encoding="utf-8")
    except Exception:
        logger.exception("Failed to read project statusline.sh at %s", project_script)
        return False

    if _MPM_MARKER not in existing:
        logger.debug(
            "Project statusline.sh at %s lacks MPM marker — leaving user copy alone",
            project_script,
        )
        return True

    # MPM-managed project copy.  If the user-level destination is missing,
    # promote ours up (so we don't lose any local customisations a user may
    # have made to an MPM-managed script before the user-level migration
    # landed).  Otherwise just remove the project copy.
    if not user_script.exists():
        try:
            user_script.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project_script, user_script)
            current_mode = user_script.stat().st_mode
            user_script.chmod(
                current_mode
                | stat.S_IRWXU
                | stat.S_IRGRP
                | stat.S_IXGRP
                | stat.S_IROTH
                | stat.S_IXOTH
            )
            logger.info(
                "Promoted MPM-managed statusline.sh from %s to %s",
                project_script,
                user_script,
            )
        except Exception:
            logger.exception(
                "Failed to copy %s → %s; leaving project copy in place",
                project_script,
                user_script,
            )
            return False

    try:
        project_script.unlink()
        logger.info("Removed legacy project-level statusline.sh at %s", project_script)
    except Exception:
        logger.exception("Failed to remove project statusline.sh at %s", project_script)
        return False

    return True


def _clean_settings(project_claude: Path) -> bool:
    """Strip MPM-owned statusLine and Stop hook entries from project settings.

    Mutations:
    - Remove ``settings["statusLine"]`` if its ``command`` substring-matches
      ``statusline.sh``.
    - Remove every Stop hook whose ``command`` substring-matches
      ``statusline.sh --clear``.  Empty ``hooks`` lists / empty Stop groups
      are pruned, as is an empty top-level ``Stop`` list and an empty
      ``hooks`` dict.

    User-owned entries (those whose command does not contain the substring)
    are left in place.

    Args:
        project_claude: Path to ``<cwd>/.claude``.

    Returns:
        True on success (including no-op), False on error.
    """
    settings_path = project_claude / "settings.json"
    if not settings_path.exists():
        logger.debug("No project settings.json at %s — nothing to clean", settings_path)
        return True

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to parse project settings.json at %s", settings_path)
        return False

    if not isinstance(raw, dict):
        logger.warning(
            "Project settings.json at %s is not a JSON object — leaving alone",
            settings_path,
        )
        return True

    settings = raw
    changed = False

    # --- statusLine ----------------------------------------------------------
    existing = settings.get("statusLine")
    if isinstance(existing, dict):
        cmd = existing.get("command", "")
        if isinstance(cmd, str) and _STATUSLINE_COMMAND_MATCH in cmd:
            del settings["statusLine"]
            changed = True
            logger.info("Removed MPM-managed statusLine entry from %s", settings_path)

    # --- Stop hooks ----------------------------------------------------------
    hooks = settings.get("hooks")
    if isinstance(hooks, dict):
        stop_groups = hooks.get("Stop")
        if isinstance(stop_groups, list):
            new_groups: list = []
            for group in stop_groups:
                if not isinstance(group, dict):
                    new_groups.append(group)
                    continue
                inner = group.get("hooks")
                if not isinstance(inner, list):
                    new_groups.append(group)
                    continue
                kept = []
                for hook in inner:
                    if isinstance(hook, dict):
                        cmd = hook.get("command", "")
                        if isinstance(cmd, str) and _STOP_HOOK_MATCH in cmd:
                            changed = True
                            logger.info(
                                "Removed MPM-managed Stop hook from %s",
                                settings_path,
                            )
                            continue
                    kept.append(hook)
                if kept:
                    group["hooks"] = kept
                    new_groups.append(group)
                else:
                    # Drop the whole group if it's left empty.
                    changed = True
            if new_groups:
                hooks["Stop"] = new_groups
            else:
                del hooks["Stop"]
                changed = True
        if not hooks:
            del settings["hooks"]
            changed = True

    if not changed:
        logger.debug(
            "No MPM-managed entries to remove from %s — skipping", settings_path
        )
        return True

    try:
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Cleaned project settings.json at %s", settings_path)
    except Exception:
        logger.exception("Failed to write project settings.json at %s", settings_path)
        return False

    return True


def run_migration(installation_dir: Path | None = None) -> bool:
    """Move legacy project-level statusline assets to the user level.

    Args:
        installation_dir: Project root to clean (default: cwd).  Only the
            CURRENT project is touched — this migration is registered to run
            once per project at startup and is a no-op for projects that
            never had a legacy install.

    Returns:
        True on success (including no-op), False on error.
    """
    project_root = installation_dir or Path.cwd()
    project_claude = project_root / ".claude"
    if not project_claude.exists():
        logger.debug("No project .claude/ at %s — nothing to migrate", project_claude)
        return True

    user_script = Path.home() / ".claude" / "hooks" / "scripts" / "statusline.sh"

    script_ok = _migrate_script(project_claude, user_script)
    settings_ok = _clean_settings(project_claude)
    return script_ok and settings_ok
