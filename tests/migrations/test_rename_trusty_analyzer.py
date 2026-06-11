"""Tests for the trusty-analyzer → trusty-analyze rename migration (issue #782).

Covers:
(a) Old ``trusty-analyzer`` MCP entry → renamed to ``trusty-analyze`` with
    canonical command/args.
(b) Idempotent no-op when already migrated or absent.
(c) When both old+new exist, stale old entry is dropped.
(d) launchd subprocess calls and plist removal are mocked so the test suite
    is hermetic and macOS-independent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.migrations import v6_5_34_rename_trusty_analyzer as mod

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_OLD_ENTRY = {
    "type": "stdio",
    "command": "trusty-analyzer",
    "args": ["mcp"],
}
_NEW_ENTRY = {
    "type": "stdio",
    "command": "trusty-analyze",
    "args": ["mcp"],
}


def _write_mcp(project_dir: Path, config: dict) -> Path:
    mcp_path = project_dir / ".mcp.json"
    mcp_path.write_text(json.dumps(config, indent=2) + "\n")
    return mcp_path


# ---------------------------------------------------------------------------
# (a) Old entry → renamed with canonical command/args
# ---------------------------------------------------------------------------


def test_old_entry_renamed(tmp_path: Path) -> None:
    """trusty-analyzer entry → renamed to trusty-analyze, command/args canonical."""
    mcp_path = _write_mcp(
        tmp_path,
        {"mcpServers": {"trusty-analyzer": dict(_OLD_ENTRY)}},
    )

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is True
    servers = json.loads(mcp_path.read_text())["mcpServers"]
    assert "trusty-analyzer" not in servers
    assert servers["trusty-analyze"] == _NEW_ENTRY


def test_old_entry_with_wrong_command_corrected(tmp_path: Path) -> None:
    """Entry keyed trusty-analyzer but with wrong command is corrected."""
    mcp_path = _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "trusty-analyzer": {
                    "type": "stdio",
                    "command": "trusty-analyzer",  # old binary name
                    "args": ["mcp"],
                }
            }
        },
    )

    mod.run_migration(project_dir=tmp_path)

    servers = json.loads(mcp_path.read_text())["mcpServers"]
    assert servers["trusty-analyze"]["command"] == "trusty-analyze"
    assert servers["trusty-analyze"]["args"] == ["mcp"]


def test_unrelated_servers_are_preserved(tmp_path: Path) -> None:
    """Other MCP server entries are left unmodified."""
    mcp_path = _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "trusty-analyzer": dict(_OLD_ENTRY),
                "trusty-search": {
                    "type": "stdio",
                    "command": "trusty-search",
                    "args": ["serve"],
                },
                "trusty-memory": {
                    "type": "stdio",
                    "command": "trusty-memory-mcp-bridge",
                    "args": [],
                },
            }
        },
    )

    mod.run_migration(project_dir=tmp_path)

    servers = json.loads(mcp_path.read_text())["mcpServers"]
    assert servers["trusty-search"] == {
        "type": "stdio",
        "command": "trusty-search",
        "args": ["serve"],
    }
    assert servers["trusty-memory"] == {
        "type": "stdio",
        "command": "trusty-memory-mcp-bridge",
        "args": [],
    }


# ---------------------------------------------------------------------------
# (b) Idempotent no-op cases
# ---------------------------------------------------------------------------


def test_already_migrated_is_noop(tmp_path: Path) -> None:
    """trusty-analyze already present and trusty-analyzer absent → no change."""
    mcp_path = _write_mcp(
        tmp_path,
        {"mcpServers": {"trusty-analyze": dict(_NEW_ENTRY)}},
    )
    original = mcp_path.read_text()

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is False
    assert mcp_path.read_text() == original


def test_absent_entry_is_noop(tmp_path: Path) -> None:
    """No trusty-analyzer entry at all → no change, returns False."""
    mcp_path = _write_mcp(
        tmp_path,
        {"mcpServers": {"some-other": {"type": "stdio", "command": "other"}}},
    )
    original = mcp_path.read_text()

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is False
    assert mcp_path.read_text() == original


def test_no_files_is_noop(tmp_path: Path) -> None:
    """Empty project dir → returns False, no files created."""
    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is False
    assert not (tmp_path / ".mcp.json").exists()


def test_idempotent_second_run(tmp_path: Path) -> None:
    """Running twice: first run modifies, second is a no-op."""
    _write_mcp(
        tmp_path,
        {"mcpServers": {"trusty-analyzer": dict(_OLD_ENTRY)}},
    )

    assert mod.run_migration(project_dir=tmp_path) is True
    assert mod.run_migration(project_dir=tmp_path) is False


# ---------------------------------------------------------------------------
# (c) Both old+new exist → drop old, keep new
# ---------------------------------------------------------------------------


def test_both_entries_drops_old(tmp_path: Path) -> None:
    """When trusty-analyzer AND trusty-analyze both exist, old is dropped."""
    mcp_path = _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "trusty-analyzer": dict(_OLD_ENTRY),
                "trusty-analyze": dict(_NEW_ENTRY),
            }
        },
    )

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is True
    servers = json.loads(mcp_path.read_text())["mcpServers"]
    assert "trusty-analyzer" not in servers
    assert servers["trusty-analyze"] == _NEW_ENTRY


def test_both_entries_new_is_unchanged(tmp_path: Path) -> None:
    """When both exist, the existing trusty-analyze entry is not overwritten."""
    custom_new = {
        "type": "stdio",
        "command": "trusty-analyze",
        "args": ["mcp"],
        "env": {"FOO": "bar"},
    }
    mcp_path = _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "trusty-analyzer": dict(_OLD_ENTRY),
                "trusty-analyze": custom_new,
            }
        },
    )

    mod.run_migration(project_dir=tmp_path)

    servers = json.loads(mcp_path.read_text())["mcpServers"]
    # Custom trusty-analyze entry preserved intact.
    assert servers["trusty-analyze"] == custom_new


# ---------------------------------------------------------------------------
# (d) launchd plist cleanup — hermetic mocks
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_plist(tmp_path: Path) -> Path:
    """Create a fake launchd plist file in a temp LaunchAgents dir."""
    launch_agents = tmp_path / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True)
    plist = launch_agents / "com.bobmatnyc.trusty-analyzer.plist"
    plist.write_text("<plist/>")
    return plist


def test_launchd_plist_removed_on_macos(tmp_path: Path, fake_plist: Path) -> None:
    """Plist file is removed and launchctl is called on macOS."""
    with (
        patch.object(mod, "_get_uid", return_value=501),
        patch("sys.platform", "darwin"),
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run,
        patch.object(Path, "home", return_value=tmp_path),
    ):
        mod._cleanup_launchd_plist()

    # launchctl was called at least once.
    assert mock_run.called
    # Plist file was removed.
    assert not fake_plist.exists()


def test_launchd_noop_when_no_plist(tmp_path: Path) -> None:
    """_cleanup_launchd_plist is a no-op when plist does not exist."""
    with (
        patch("sys.platform", "darwin"),
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run,
        patch.object(Path, "home", return_value=tmp_path),
    ):
        mod._cleanup_launchd_plist()

    # launchctl should NOT have been called — plist didn't exist.
    assert not mock_run.called


def test_launchd_noop_on_non_macos(tmp_path: Path, fake_plist: Path) -> None:
    """_cleanup_launchd_plist is a no-op on non-macOS platforms."""
    with (
        patch("sys.platform", "linux"),
        patch.object(Path, "home", return_value=tmp_path),
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run,
    ):
        mod._cleanup_launchd_plist()

    assert not mock_run.called
    # Plist left untouched (we're not on macOS).
    assert fake_plist.exists()


def test_launchd_subprocess_error_swallowed(tmp_path: Path, fake_plist: Path) -> None:
    """A subprocess.TimeoutExpired from launchctl does not propagate."""
    import subprocess

    with (
        patch("sys.platform", "darwin"),
        patch.object(Path, "home", return_value=tmp_path),
        patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["launchctl"], timeout=5),
        ),
    ):
        # Must not raise.
        mod._cleanup_launchd_plist()

    # Plist may or may not be removed depending on which step failed; the key
    # assertion is that no exception escaped.


def test_run_migration_triggers_launchd_cleanup(tmp_path: Path) -> None:
    """run_migration calls _cleanup_launchd_plist (integration-level check)."""
    with patch.object(
        mod, "_cleanup_launchd_plist", return_value=False
    ) as mock_cleanup:
        mod.run_migration(project_dir=tmp_path)

    mock_cleanup.assert_called_once()


def test_run_migration_returns_true_for_plist_only_cleanup(tmp_path: Path) -> None:
    """run_migration returns True when only the plist was cleaned (no MCP file changed).

    Previously _cleanup_launchd_plist() returned None, so plist-only runs
    silently returned False even though work was done.  Now the bool is captured
    and OR'd into the return value.
    """
    with patch.object(mod, "_cleanup_launchd_plist", return_value=True):
        result = mod.run_migration(project_dir=tmp_path)

    assert result is True


# ---------------------------------------------------------------------------
# Fix 2: stale fields on the old entry must NOT carry over to the renamed entry
# ---------------------------------------------------------------------------


def test_stale_env_field_not_carried_to_renamed_entry(tmp_path: Path) -> None:
    """Extra/stale fields on the old trusty-analyzer entry are NOT inherited.

    When only trusty-analyzer is present and it carries extra fields (e.g. an
    ``env`` dict pointing at the old binary path), those fields must be dropped.
    The new trusty-analyze entry must be exactly the canonical shape.
    """
    mcp_path = _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "trusty-analyzer": {
                    "type": "stdio",
                    "command": "trusty-analyzer",
                    "args": ["mcp"],
                    "env": {"BINARY_PATH": "/usr/local/bin/trusty-analyzer"},
                    "stale_extra": "should-be-gone",
                }
            }
        },
    )

    mod.run_migration(project_dir=tmp_path)

    servers = json.loads(mcp_path.read_text())["mcpServers"]
    assert "trusty-analyzer" not in servers
    new_entry = servers["trusty-analyze"]
    # Must be exactly the canonical entry — no env, no stale_extra.
    assert new_entry == _NEW_ENTRY
    assert "env" not in new_entry
    assert "stale_extra" not in new_entry
