"""Tests for the legacy project-level statusline cleanup (issue #939).

WHAT: Exercises ``_clean_settings`` in
:mod:`claude_mpm.migrations.migrate_statusline_user_level`, the migration that
strips legacy project-scoped ``statusLine`` / Stop-hook entries from
``<project>/.claude/settings.json``.

WHY: This removal path identified MPM-owned entries by substring-matching the
bundled ``statusline.sh`` path, so it could not recognise a CUSTOM-policy entry
as MPM's and left the ``_mpm`` marker behind. Simply asking "is it MPM-owned?"
instead would have deleted the user's own command, so the path now acts on the
shared three-way disposition. These tests pin all four entry shapes plus the
Stop-hook behaviour that deliberately did not change.

References: https://github.com/bobmatnyc/claude-mpm/issues/939
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from claude_mpm.migrations.migrate_statusline_user_level import _clean_settings

if TYPE_CHECKING:
    from pathlib import Path


def _seed(project_claude: Path, settings: dict) -> Path:
    project_claude.mkdir(parents=True, exist_ok=True)
    path = project_claude / "settings.json"
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_bundled_entry_is_removed(tmp_path: Path) -> None:
    """Regression guard: a bundled-script entry is still deleted outright.

    Why: This is MPM's own MANAGED artifact; the disposition refactor must not
    weaken the cleanup that motivated this migration in the first place.
    """
    project_claude = tmp_path / ".claude"
    path = _seed(
        project_claude,
        {
            "statusLine": {
                "type": "command",
                "command": ".claude/hooks/scripts/statusline.sh",
                "_mpm": True,
            },
            "keepme": True,
        },
    )

    assert _clean_settings(project_claude) is True

    data = _read(path)
    assert "statusLine" not in data
    assert data["keepme"] is True


def test_legacy_marker_less_bundled_entry_is_removed(tmp_path: Path) -> None:
    """A pre-marker legacy entry is still recognised by the command substring."""
    project_claude = tmp_path / ".claude"
    path = _seed(
        project_claude,
        {
            "statusLine": {
                "type": "command",
                "command": ".claude/hooks/scripts/statusline.sh",
            }
        },
    )

    assert _clean_settings(project_claude) is True
    assert "statusLine" not in _read(path)


def test_custom_entry_keeps_command_and_loses_marker(tmp_path: Path) -> None:
    """A marker-bearing CUSTOM entry keeps ``command`` and drops ``_mpm``.

    Why: The command in a CUSTOM entry belongs to the user. claude-mpm
    relinquishes ownership on cleanup without discarding that configuration —
    the core requirement of issue #939.
    """
    project_claude = tmp_path / ".claude"
    path = _seed(
        project_claude,
        {"statusLine": {"type": "command", "command": "/opt/mybar --x", "_mpm": True}},
    )

    assert _clean_settings(project_claude) is True

    data = _read(path)
    assert data["statusLine"] == {"type": "command", "command": "/opt/mybar --x"}


def test_user_authored_entry_is_untouched(tmp_path: Path) -> None:
    """No marker and a non-bundled command means the file is not rewritten."""
    project_claude = tmp_path / ".claude"
    original = {"statusLine": {"type": "command", "command": "/opt/mybar"}}
    path = _seed(project_claude, original)

    assert _clean_settings(project_claude) is True
    assert _read(path) == original


def test_stop_hooks_still_pruned_and_user_hooks_kept(tmp_path: Path) -> None:
    """Stop-hook handling is unchanged: only ``--clear`` hooks are removed.

    Why: claude-mpm never installs a ``--clear`` hook for a custom command, so
    the command substring remains the correct ownership signal for Stop hooks and
    the disposition refactor deliberately leaves that logic alone.
    """
    project_claude = tmp_path / ".claude"
    path = _seed(
        project_claude,
        {
            "hooks": {
                "Stop": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"command": ".claude/hooks/scripts/statusline.sh --clear"},
                            {"command": "/my/own/on-stop.sh"},
                        ],
                    }
                ]
            }
        },
    )

    assert _clean_settings(project_claude) is True

    data = _read(path)
    assert data["hooks"]["Stop"][0]["hooks"] == [{"command": "/my/own/on-stop.sh"}]


def test_missing_settings_file_is_a_no_op(tmp_path: Path) -> None:
    """A project with no settings.json is a clean success."""
    project_claude = tmp_path / ".claude"
    project_claude.mkdir(parents=True)

    assert _clean_settings(project_claude) is True
    assert not (project_claude / "settings.json").exists()
