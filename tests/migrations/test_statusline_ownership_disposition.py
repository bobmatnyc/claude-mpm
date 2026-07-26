"""Tests for statusLine ownership-vs-removability classification (issue #939).

WHAT: Exercises ``classify_statusline_entry``, ``strip_statusline_marker`` and the
``_cleanup_global_statusline_settings`` removal path in
:mod:`claude_mpm.migrations.migrate_statusline_autoconfig`.

WHY: PR #936 made statusLine ownership an explicit recorded fact (``_mpm: True``).
Ownership alone is not licence to delete: under the CUSTOM policy claude-mpm
stamps that marker onto an entry whose ``command`` is the *user's*, so a removal
path that deletes every entry it owns destroys user configuration. These tests
pin the three-way disposition — REMOVE the bundled-script entry, DISOWN (marker
only) a custom one, LEAVE a user-authored one — that every removal path shares.

References: https://github.com/bobmatnyc/claude-mpm/issues/939
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from claude_mpm.migrations.migrate_statusline_autoconfig import (
    StatuslineDisposition,
    _cleanup_global_statusline_settings,
    _is_mpm_owned_statusline,
    classify_statusline_entry,
    strip_statusline_marker,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# 1. classify_statusline_entry
# ---------------------------------------------------------------------------


def test_bundled_script_entry_is_removable() -> None:
    """A marked entry pointing at the bundled script is MPM's own artifact.

    Why: This is the MANAGED-policy entry claude-mpm writes for itself, so an
    uninstall must delete it outright — that is today's behaviour and the
    disposition must preserve it.
    """
    entry = {
        "type": "command",
        "command": "/home/u/.claude/hooks/scripts/statusline.sh",
        "_mpm": True,
    }
    assert classify_statusline_entry(entry) is StatuslineDisposition.REMOVE


def test_legacy_marker_less_bundled_entry_is_removable() -> None:
    """A pre-marker entry is still recognised via the command substring.

    Why: Entries written by MPM versions predating the ``_mpm`` marker carry no
    marker at all; the substring fallback is the only signal available for them
    and dropping it would strand MPM's own footprint on every older install.
    """
    entry = {"type": "command", "command": ".claude/hooks/scripts/statusline.sh"}
    assert classify_statusline_entry(entry) is StatuslineDisposition.REMOVE


def test_custom_marked_entry_is_disowned_not_removed() -> None:
    """A marker-bearing entry whose command is the user's must only be disowned.

    Why: This is the whole point of #939. Under the CUSTOM policy MPM writes the
    user's command and stamps the marker, so treating "MPM-owned" as "safe to
    delete" would erase the user's own statusline configuration.
    """
    entry = {"type": "command", "command": "/opt/mybar --fancy", "_mpm": True}
    assert classify_statusline_entry(entry) is StatuslineDisposition.DISOWN


def test_user_authored_entry_is_left_alone() -> None:
    """No marker plus a non-bundled command means claude-mpm never wrote it."""
    entry = {"type": "command", "command": "/opt/mybar --fancy"}
    assert classify_statusline_entry(entry) is StatuslineDisposition.LEAVE


def test_non_dict_entries_are_left_alone() -> None:
    """Malformed settings must never be classified as removable."""
    for value in (None, "not-a-dict", 42, [], {"command": 5}):
        assert classify_statusline_entry(value) is StatuslineDisposition.LEAVE


def test_ownership_predicate_agrees_with_disposition() -> None:
    """``_is_mpm_owned_statusline`` is exactly "disposition is not LEAVE".

    Why: The ownership question and the removability question must be derived
    from one classification so they can never drift apart again.
    """
    for entry in (
        {"command": "/x/statusline.sh"},
        {"command": "/x/statusline.sh", "_mpm": True},
        {"command": "/opt/mybar", "_mpm": True},
        {"command": "/opt/mybar"},
        None,
    ):
        expected = classify_statusline_entry(entry) is not StatuslineDisposition.LEAVE
        assert _is_mpm_owned_statusline(entry) is expected


# ---------------------------------------------------------------------------
# 2. strip_statusline_marker
# ---------------------------------------------------------------------------


def test_strip_marker_preserves_every_other_key() -> None:
    """Disowning removes only ``_mpm`` — ``command`` above all must survive."""
    entry = {"type": "command", "command": "/opt/mybar", "_mpm": True, "padding": 3}

    assert strip_statusline_marker(entry) is True
    assert entry == {"type": "command", "command": "/opt/mybar", "padding": 3}


def test_strip_marker_on_unmarked_entry_is_a_no_op() -> None:
    """A marker-less entry is reported unchanged and is not mutated."""
    entry = {"type": "command", "command": "/opt/mybar"}

    assert strip_statusline_marker(entry) is False
    assert entry == {"type": "command", "command": "/opt/mybar"}


# ---------------------------------------------------------------------------
# 3. _cleanup_global_statusline_settings (the issue #924 global self-heal)
# ---------------------------------------------------------------------------


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_global_self_heal_removes_bundled_entry(tmp_path: Path) -> None:
    """Regression guard: the bundled-script entry is still deleted outright."""
    settings = tmp_path / "settings.json"
    _write(
        settings,
        {
            "statusLine": {"command": "/legacy/statusline.sh", "_mpm": True},
            "keepme": True,
        },
    )

    assert _cleanup_global_statusline_settings(settings) is True

    data = _read(settings)
    assert "statusLine" not in data
    assert data["keepme"] is True


def test_global_self_heal_disowns_custom_entry(tmp_path: Path) -> None:
    """A marker-bearing custom entry keeps its command and loses the marker.

    Why: The self-heal used to delete anything ``_is_mpm_owned_statusline``
    matched, which would have taken the user's own command with it.
    """
    settings = tmp_path / "settings.json"
    _write(
        settings,
        {"statusLine": {"type": "command", "command": "/opt/mybar", "_mpm": True}},
    )

    assert _cleanup_global_statusline_settings(settings) is True

    data = _read(settings)
    assert data["statusLine"] == {"type": "command", "command": "/opt/mybar"}


def test_global_self_heal_leaves_user_authored_entry(tmp_path: Path) -> None:
    """An entry with no marker and a non-bundled command is untouched."""
    settings = tmp_path / "settings.json"
    original = {"statusLine": {"type": "command", "command": "/opt/mybar"}}
    _write(settings, original)

    assert _cleanup_global_statusline_settings(settings) is True
    assert _read(settings) == original
