"""
Standalone update-statusline command for claude-mpm.

WHY: Users sometimes need to refresh the MPM-managed statusline.sh
without starting a full Claude session (e.g. after pulling an update
that ships a newer statusline template).  The regular ``claude-mpm run``
path already invokes the statusline autoconfig migration on every
startup, but for MPM-managed scripts the bundled content is auto-
upgraded — only user-customised scripts (lacking the
``# claude-mpm-managed:`` marker) are skipped.

This command calls the same migration in ``force=True`` mode, so a
user-customised statusline.sh is also overwritten with the canonical
version bundled in the installed package.

The script and settings live at the USER level
(``~/.claude/hooks/scripts/statusline.sh`` and
``~/.claude/settings.json``); the legacy ``--project-dir`` flag is
retained for compatibility but is ignored.

DESIGN DECISIONS:
- Reuses ``migrations.migrate_statusline_autoconfig.run_migration`` so
  there is a single source of truth for statusline deployment logic.
- Exits 0 on success, 1 on failure — easy to chain in shell scripts.
- Prints a one-line confirmation so interactive users get clear feedback.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

logger = logging.getLogger(__name__)

# Absolute path to the user-level statusline script (single source of truth
# for the path the CLI prints back at the user on success).
_USER_SCRIPT_PATH = Path.home() / ".claude" / "hooks" / "scripts" / "statusline.sh"


def add_update_statusline_parser(subparsers) -> argparse.ArgumentParser:
    """Register the ``update-statusline`` subcommand on the main parser."""
    parser = subparsers.add_parser(
        "update-statusline",
        help="Force-refresh the MPM-managed statusline.sh at the user level",
        description=(
            "Re-run the statusline autoconfig migration with force=True so the "
            "MPM-managed ~/.claude/hooks/scripts/statusline.sh is overwritten "
            "with the canonical version bundled in the installed package. "
            "User-customised scripts (without the MPM marker) are also "
            "overwritten in --force mode."
        ),
    )
    # Retained for backwards compatibility; the migration always targets
    # ~/.claude/ regardless of this value.
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help=(
            "Deprecated: ignored.  The statusline now lives at the user level "
            "(~/.claude/) and applies to every project."
        ),
    )
    return parser


def run_update_statusline(args) -> int:
    """Execute the statusline update.

    Args:
        args: Parsed argparse namespace. ``project_dir`` is accepted for
            backwards compatibility but ignored.

    Returns:
        0 on success, 1 on failure.
    """
    # ``project_dir`` is accepted for backwards compatibility but the
    # migration ignores it — it always targets ~/.claude/.
    _ = getattr(args, "project_dir", None)

    try:
        from ...migrations.migrate_statusline_autoconfig import (
            run_migration as _configure_statusline,
        )
    except Exception as exc:  # pragma: no cover - import should not fail
        print(f"Statusline update failed: could not load migration ({exc})")
        return 1

    try:
        ok = _configure_statusline(force=True)
    except Exception as exc:
        print(f"Statusline update failed: {exc}")
        logger.exception("update-statusline: migration raised unexpectedly")
        return 1

    if ok:
        print(f"Statusline updated ({_USER_SCRIPT_PATH}).")
        return 0

    print("Statusline update failed: migration returned an error status.")
    return 1
