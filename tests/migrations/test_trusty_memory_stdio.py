"""Tests for the trusty-memory stdio migration (v6_5_36).

The migration rewrites stale ``trusty-memory-mcp-bridge`` MCP entries to the
canonical ``trusty-memory serve --stdio`` form.  All tests are hermetic: no
real binaries, no network I/O.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_mpm.migrations import v6_5_36_trusty_memory_stdio as mod

# Canonical stdio entry for trusty-memory after the migration.
_STDIO_ENTRY = {
    "type": "stdio",
    "command": "trusty-memory",
    "args": ["serve", "--stdio"],
}

# Old bridge entry that this migration replaces.
_BRIDGE_ENTRY = {
    "type": "stdio",
    "command": "trusty-memory-mcp-bridge",
    "args": [],
}


def _write_mcp(project_dir: Path, config: dict) -> Path:
    mcp_path = project_dir / ".mcp.json"
    mcp_path.write_text(json.dumps(config, indent=2) + "\n")
    return mcp_path


# ---------------------------------------------------------------------------
# Core rewrite behaviour
# ---------------------------------------------------------------------------


def test_bridge_entry_rewritten_to_stdio(tmp_path: Path) -> None:
    """Bridge command → rewritten to the canonical stdio form."""
    mcp_path = _write_mcp(
        tmp_path,
        {"mcpServers": {"trusty-memory": dict(_BRIDGE_ENTRY)}},
    )

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is True
    servers = json.loads(mcp_path.read_text())["mcpServers"]
    assert servers["trusty-memory"] == _STDIO_ENTRY


def test_already_stdio_is_noop(tmp_path: Path) -> None:
    """Already-stdio entry → no change, returns False, file untouched."""
    mcp_path = _write_mcp(
        tmp_path,
        {"mcpServers": {"trusty-memory": dict(_STDIO_ENTRY)}},
    )
    original = mcp_path.read_text()

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is False
    assert mcp_path.read_text() == original


def test_absent_entry_is_noop(tmp_path: Path) -> None:
    """No trusty-memory entry at all → no change, returns False."""
    mcp_path = _write_mcp(
        tmp_path,
        {"mcpServers": {"some-other-server": {"type": "stdio", "command": "whatever"}}},
    )
    original = mcp_path.read_text()

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is False
    assert mcp_path.read_text() == original


def test_no_files_is_noop(tmp_path: Path) -> None:
    """Empty project dir (no config files) → no change, returns False."""
    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is False
    assert not (tmp_path / ".mcp.json").exists()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_idempotent_after_rewrite(tmp_path: Path) -> None:
    """Running twice: first run rewrites, second run is a no-op."""
    _write_mcp(
        tmp_path,
        {"mcpServers": {"trusty-memory": dict(_BRIDGE_ENTRY)}},
    )

    assert mod.run_migration(project_dir=tmp_path) is True
    assert mod.run_migration(project_dir=tmp_path) is False


# ---------------------------------------------------------------------------
# Unrelated entries are preserved
# ---------------------------------------------------------------------------


def test_search_and_other_entries_untouched(tmp_path: Path) -> None:
    """trusty-search and other entries must never be modified."""
    mcp_path = _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "trusty-memory": dict(_BRIDGE_ENTRY),
                "trusty-search": {
                    "type": "stdio",
                    "command": "trusty-search",
                    "args": ["serve"],
                },
                "unrelated": {"type": "stdio", "command": "other"},
            }
        },
    )

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is True
    servers = json.loads(mcp_path.read_text())["mcpServers"]
    # Memory repaired to stdio...
    assert servers["trusty-memory"] == _STDIO_ENTRY
    # ...search and unrelated entries left exactly as they were.
    assert servers["trusty-search"] == {
        "type": "stdio",
        "command": "trusty-search",
        "args": ["serve"],
    }
    assert servers["unrelated"] == {"type": "stdio", "command": "other"}


# ---------------------------------------------------------------------------
# User-level MCP config
# ---------------------------------------------------------------------------


def test_user_level_mcp_json_rewritten(tmp_path: Path) -> None:
    """Bridge entry in ~/.claude/.mcp.json → also rewritten."""
    home = tmp_path / "home"
    claude_dir = home / ".claude"
    claude_dir.mkdir(parents=True)
    user_mcp = claude_dir / ".mcp.json"
    user_mcp.write_text(
        json.dumps({"mcpServers": {"trusty-memory": dict(_BRIDGE_ENTRY)}}, indent=2)
        + "\n"
    )

    # Project dir has no .mcp.json.
    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    # Patch Path.home() to point at our isolated home.
    from unittest.mock import patch

    with patch.object(Path, "home", lambda: home):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is True
    servers = json.loads(user_mcp.read_text())["mcpServers"]
    assert servers["trusty-memory"] == _STDIO_ENTRY


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------


def test_malformed_json_is_skipped_gracefully(tmp_path: Path) -> None:
    """Malformed JSON in .mcp.json → skip, no exception, return False."""
    mcp_path = tmp_path / ".mcp.json"
    mcp_path.write_text("{ not valid json")

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is False
    # File is untouched (no partial write).
    assert mcp_path.read_text() == "{ not valid json"


def test_missing_mcp_servers_key_is_noop(tmp_path: Path) -> None:
    """JSON file without 'mcpServers' key → no-op, no exception."""
    mcp_path = _write_mcp(tmp_path, {"someOtherKey": "value"})
    original = mcp_path.read_text()

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is False
    assert mcp_path.read_text() == original


def test_atomic_write_no_tmp_left_on_success(tmp_path: Path) -> None:
    """Successful rewrite must not leave a .tmp sibling behind."""
    _write_mcp(
        tmp_path,
        {"mcpServers": {"trusty-memory": dict(_BRIDGE_ENTRY)}},
    )

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is True
    # The atomic write uses a sibling .tmp file; it must be cleaned up.
    assert not (tmp_path / ".mcp.json.tmp").exists()


def test_atomic_write_result_is_valid_json(tmp_path: Path) -> None:
    """After rewrite, .mcp.json must be parseable and contain the canonical entry."""
    _write_mcp(
        tmp_path,
        {"mcpServers": {"trusty-memory": dict(_BRIDGE_ENTRY)}},
    )

    mod.run_migration(project_dir=tmp_path)

    mcp_path = tmp_path / ".mcp.json"
    # File must be valid JSON (not truncated).
    data = json.loads(mcp_path.read_text())
    assert data["mcpServers"]["trusty-memory"] == _STDIO_ENTRY


# ---------------------------------------------------------------------------
# _needs_rewrite helper
# ---------------------------------------------------------------------------


def test_needs_rewrite_true_for_bridge() -> None:
    """_needs_rewrite returns True for the old bridge command."""
    assert (
        mod._needs_rewrite({"command": "trusty-memory-mcp-bridge", "args": []}) is True
    )


def test_needs_rewrite_false_for_canonical() -> None:
    """_needs_rewrite returns False when already canonical."""
    assert mod._needs_rewrite(_STDIO_ENTRY) is False


def test_needs_rewrite_false_for_non_dict() -> None:
    """_needs_rewrite returns False for non-dict entries (no AttributeError)."""
    assert mod._needs_rewrite(None) is False
    assert mod._needs_rewrite("string") is False
    assert mod._needs_rewrite(42) is False


# ---------------------------------------------------------------------------
# _fix_servers helper
# ---------------------------------------------------------------------------


def test_fix_servers_rewrites_bridge() -> None:
    """_fix_servers mutates dict in-place and returns True."""
    servers = {"trusty-memory": dict(_BRIDGE_ENTRY)}
    result = mod._fix_servers(servers)
    assert result is True
    assert servers["trusty-memory"] == _STDIO_ENTRY


def test_fix_servers_noop_on_canonical() -> None:
    """_fix_servers returns False when entry already canonical."""
    servers = {"trusty-memory": dict(_STDIO_ENTRY)}
    result = mod._fix_servers(servers)
    assert result is False
    assert servers["trusty-memory"] == _STDIO_ENTRY


def test_fix_servers_noop_on_absent() -> None:
    """_fix_servers returns False when trusty-memory key is absent."""
    servers: dict = {}
    result = mod._fix_servers(servers)
    assert result is False


def test_fix_servers_noop_on_non_dict() -> None:
    """_fix_servers returns False for non-dict servers (no TypeError)."""
    assert mod._fix_servers(None) is False
    assert mod._fix_servers([]) is False


# ---------------------------------------------------------------------------
# Registry: migration is registered with the correct id/version
# ---------------------------------------------------------------------------


def test_migration_registered_in_registry() -> None:
    """The migration is registered in the MIGRATIONS list with correct id/version."""
    from claude_mpm.migrations.registry import MIGRATIONS

    matching = [m for m in MIGRATIONS if m.id == "v6_5_36_trusty_memory_stdio"]
    assert len(matching) == 1, (
        f"Expected exactly one migration with id 'v6_5_36_trusty_memory_stdio', "
        f"found: {[m.id for m in MIGRATIONS]}"
    )
    migration = matching[0]
    assert migration.version == "6.5.36"
    assert "trusty-memory" in migration.description.lower()
