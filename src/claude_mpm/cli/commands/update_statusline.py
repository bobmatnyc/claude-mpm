"""
Standalone update-statusline command for claude-mpm.

WHY: Users sometimes need to refresh the MPM-managed statusline.sh in a
project without starting a full Claude session (e.g. after pulling an
update that ships a newer statusline template).  The regular
``claude-mpm run`` path already invokes the statusline autoconfig
migration on every startup, but that path is idempotent and skips
already-installed scripts — it won't upgrade an existing MPM-managed
copy unless explicitly asked.

This command calls the same migration in ``force=True`` mode, so the
MPM-managed statusline.sh is overwritten with the canonical version
bundled in the installed package.  User-customised scripts (those
lacking the ``# claude-mpm-managed:`` marker) are preserved.

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


def add_update_statusline_parser(subparsers) -> argparse.ArgumentParser:
    """Register the ``update-statusline`` subcommand on the main parser."""
    parser = subparsers.add_parser(
        "update-statusline",
        help="Force-refresh the MPM-managed statusline.sh in the current project",
        description=(
            "Re-run the statusline autoconfig migration with force=True so the "
            "MPM-managed .claude/hooks/scripts/statusline.sh is overwritten with "
            "the canonical version bundled in the installed package. "
            "User-customised scripts (without the MPM marker) are preserved."
        ),
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory to update (defaults to current working directory).",
    )
    return parser


def run_update_statusline(args) -> int:
    """Execute the statusline update.

    Args:
        args: Parsed argparse namespace. Recognises ``project_dir`` (optional).

    Returns:
        0 on success, 1 on failure.
    """
    project_dir = getattr(args, "project_dir", None) or Path.cwd()

    try:
        from ...migrations.migrate_statusline_autoconfig import (
            run_migration as _configure_statusline,
        )
    except Exception as exc:  # pragma: no cover - import should not fail
        print(f"Statusline update failed: could not load migration ({exc})")
        return 1

    try:
        ok = _configure_statusline(installation_dir=project_dir, force=True)
    except Exception as exc:
        print(f"Statusline update failed: {exc}")
        logger.exception("update-statusline: migration raised unexpectedly")
        return 1

    if ok:
        print(
            f"Statusline updated ({project_dir / '.claude/hooks/scripts/statusline.sh'})."
        )
        return 0

    print("Statusline update failed: migration returned an error status.")
    return 1
