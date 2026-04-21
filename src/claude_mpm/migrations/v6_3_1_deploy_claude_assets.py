"""
Migration: Deploy hooks/scripts/statusline.sh and settings.json from templates (v6.3.1).

Deploys two assets into .claude/ if they are missing:
- hooks/scripts/statusline.sh  — created if missing; made executable (0o755)
- settings.json                — created ONLY if it does not exist; never overwritten

Both operations are idempotent: re-running the migration leaves existing files
untouched.

Asset content is loaded from the installed package via importlib.resources
rather than being embedded as string literals.
"""

import logging
import stat
from importlib.resources import files
from pathlib import Path

logger = logging.getLogger(__name__)

# Marker line that identifies an MPM-managed statusline.sh.
# Any file containing this string will be treated as an official MPM-owned
# copy and will be overwritten when the template has been updated.
MPM_MARKER = "# claude-mpm-managed:"


def run_migration(installation_dir: Path | None = None, force: bool = False) -> bool:
    """Deploy statusline.sh and settings.json into .claude/.

    Args:
        installation_dir: Root of the project (default: cwd)
        force: If True, overwrite ``statusline.sh`` with the bundled template
            regardless of whether the existing file carries the MPM marker.
            Intended for explicit user-driven refreshes (see
            ``claude-mpm update-statusline``).  When False (default), a
            pre-existing file without the marker is preserved.

    Returns:
        True on success
    """
    project_root = installation_dir or Path.cwd()
    claude_dir = project_root / ".claude"

    # Ensure .claude/ exists
    claude_dir.mkdir(parents=True, exist_ok=True)

    _deploy_statusline(claude_dir, force=force)
    _deploy_settings(claude_dir)

    return True


def _deploy_statusline(claude_dir: Path, force: bool = False) -> None:
    """Deploy statusline.sh.

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
    """Deploy settings.json only if it does not already exist."""
    target = claude_dir / "settings.json"

    if target.exists():
        logger.debug("Skipping settings.json: already exists at %s", target)
        return

    content = (
        files("claude_mpm") / "templates" / "claude" / "settings.json"
    ).read_text(encoding="utf-8")

    target.write_text(content, encoding="utf-8")
    logger.info("Created settings.json at %s", target)
