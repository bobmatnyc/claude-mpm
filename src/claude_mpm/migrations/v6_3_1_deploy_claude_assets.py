"""
Migration: Deploy hooks/scripts/statusline.sh and settings.json from templates
to the USER level (v6.3.1, updated v6.3.2).

Deploys two assets into ``~/.claude/`` (NOT into ``<project>/.claude/``):
- ``hooks/scripts/statusline.sh``  — created if missing; made executable (0o755).
  Existing MPM-managed copies are upgraded to the bundled template; user-
  customised copies (no MPM marker) are preserved unless ``force=True``.
- ``settings.json``                — created ONLY if it does not exist; never
  overwritten.  When created, the bundled template is patched on the fly so
  ``statusLine.command`` points at the absolute user-level script path.

Both operations are idempotent: re-running the migration leaves a fully
provisioned environment untouched.

Asset content is loaded from the installed package via importlib.resources
rather than being embedded as string literals.
"""

import json
import logging
import stat
from importlib.resources import files
from pathlib import Path

logger = logging.getLogger(__name__)

# Marker line that identifies an MPM-managed statusline.sh.
# Any file containing this string will be treated as an official MPM-owned
# copy and will be overwritten when the template has been updated.
MPM_MARKER = "# claude-mpm-managed:"

# Absolute path to the user-level statusline script.  Used for both the
# script destination and the absolute command path injected into a freshly
# created ``~/.claude/settings.json``.
_USER_SCRIPT_PATH = Path.home() / ".claude" / "hooks" / "scripts" / "statusline.sh"


def run_migration(installation_dir: Path | None = None, force: bool = False) -> bool:
    """Deploy statusline.sh and settings.json into ``~/.claude/``.

    Args:
        installation_dir: Accepted for backwards compatibility but ignored —
            this migration always targets ``~/.claude/`` regardless of the
            project from which it is invoked.
        force: If True, overwrite ``statusline.sh`` with the bundled template
            regardless of whether the existing file carries the MPM marker.
            Intended for explicit user-driven refreshes (see
            ``claude-mpm update-statusline``).  When False (default), a
            pre-existing file without the marker is preserved.

    Returns:
        True on success
    """
    # Note: ``installation_dir`` is intentionally ignored.  Earlier versions
    # wrote to ``<project>/.claude/``; we now operate at the user level so a
    # single statusline configuration applies to every project.
    _ = installation_dir
    user_claude_dir = Path.home() / ".claude"

    # Ensure ~/.claude/ exists.
    user_claude_dir.mkdir(parents=True, exist_ok=True)

    _deploy_statusline(user_claude_dir, force=force)
    _deploy_settings(user_claude_dir)

    return True


def _deploy_statusline(claude_dir: Path, force: bool = False) -> None:
    """Deploy statusline.sh into ``<claude_dir>/hooks/scripts/``.

    Policy:
    - File absent → write canonical template.
    - File present with MPM marker → upgrade to canonical template.
    - File present without MPM marker:
        * ``force=True``  → overwrite (user explicitly asked for the update).
        * ``force=False`` → skip (respect user customisations).
    """
    scripts_dir = claude_dir / "hooks" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    target = scripts_dir / "statusline.sh"

    content = (
        files("claude_mpm")
        / "templates"
        / "claude"
        / "hooks"
        / "scripts"
        / "statusline.sh"
    ).read_text(encoding="utf-8")

    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if MPM_MARKER in existing:
            if existing == content:
                logger.debug("statusline.sh is already up to date, skipping")
            else:
                target.write_text(content, encoding="utf-8")
                logger.info("Upgraded MPM-managed statusline.sh at %s", target)
        elif force:
            target.write_text(content, encoding="utf-8")
            logger.info(
                "Replaced statusline.sh at %s with canonical MPM version "
                "(force mode; previous file lacked the MPM marker)",
                target,
            )
        else:
            logger.debug(
                "statusline.sh is user-customized, skipping overwrite at %s", target
            )
    else:
        target.write_text(content, encoding="utf-8")
        logger.info("Deployed statusline.sh to %s", target)

    # Always ensure executable bit is set (chmod 0o755)
    current_mode = target.stat().st_mode
    target.chmod(
        current_mode
        | stat.S_IRWXU
        | stat.S_IRGRP
        | stat.S_IXGRP
        | stat.S_IROTH
        | stat.S_IXOTH
    )


def _deploy_settings(claude_dir: Path) -> None:
    """Deploy settings.json only if it does not already exist.

    The bundled template ships with ``statusLine.command`` set to the legacy
    project-relative path ``.claude/hooks/scripts/statusline.sh``.  When we
    write the template into ``~/.claude/`` we patch that field to the
    absolute user-level path so Claude Code can locate the script regardless
    of the current working directory.
    """
    target = claude_dir / "settings.json"

    if target.exists():
        logger.debug("Skipping settings.json: already exists at %s", target)
        return

    raw = (files("claude_mpm") / "templates" / "claude" / "settings.json").read_text(
        encoding="utf-8"
    )

    # Patch the statusLine.command to use the absolute user-level path so
    # the entry is correct in ~/.claude/settings.json (which is project-
    # independent).  Falls back to the raw template on any parse failure.
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("statusLine"), dict):
            data["statusLine"]["command"] = str(_USER_SCRIPT_PATH)
            content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        else:
            content = raw
    except json.JSONDecodeError:
        logger.warning(
            "Bundled settings.json template is not valid JSON; writing as-is"
        )
        content = raw

    target.write_text(content, encoding="utf-8")
    logger.info("Created settings.json at %s", target)
