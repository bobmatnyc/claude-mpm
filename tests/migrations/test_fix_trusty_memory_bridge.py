"""Tests for the trusty-memory bridge repair migration (issue #567).

The migration rewrites broken ``trusty-memory`` MCP entries
(``command="trusty-memory"`` with ``"--mcp"`` in ``args``) to the dedicated
bridge form ``command="trusty-memory-mcp-bridge", args=[]``.
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - used at runtime in fixtures & call sites

from claude_mpm.migrations import migrate_fix_trusty_memory_bridge as mod

_BRIDGE_ENTRY = {
    "type": "stdio",
    "command": "trusty-memory-mcp-bridge",
    "args": [],
}


def _write_mcp(project_dir: Path, config: dict) -> Path:
    mcp_path = project_dir / ".mcp.json"
    mcp_path.write_text(json.dumps(config, indent=2) + "\n")
    return mcp_path


def test_broken_entry_is_fixed(tmp_path: Path) -> None:
    """Broken serve/--mcp entry → rewritten to the bridge form."""
    mcp_path = _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "trusty-memory": {
                    "type": "stdio",
                    "command": "trusty-memory",
                    "args": ["serve", "--mcp"],
                }
            }
        },
    )

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is True
    servers = json.loads(mcp_path.read_text())["mcpServers"]
    assert servers["trusty-memory"] == _BRIDGE_ENTRY


def test_variant_broken_form_is_fixed(tmp_path: Path) -> None:
    """Variant with extra flags but containing --mcp → fixed (presence match)."""
    mcp_path = _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "trusty-memory": {
                    "type": "stdio",
                    "command": "trusty-memory",
                    "args": ["serve", "--palace", "claude-mpm", "--mcp"],
                }
            }
        },
    )

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is True
    servers = json.loads(mcp_path.read_text())["mcpServers"]
    assert servers["trusty-memory"] == _BRIDGE_ENTRY


def test_already_fixed_is_noop(tmp_path: Path) -> None:
    """Already-bridged entry → no change, returns False, file untouched."""
    mcp_path = _write_mcp(
        tmp_path,
        {"mcpServers": {"trusty-memory": dict(_BRIDGE_ENTRY)}},
    )
    original = mcp_path.read_text()

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is False
    assert mcp_path.read_text() == original


def test_absent_entry_is_noop(tmp_path: Path) -> None:
    """No trusty-memory entry at all → no change, returns False."""
    mcp_path = _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "some-other-server": {"type": "stdio", "command": "whatever"}
            }
        },
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


def test_search_and_analyzer_untouched(tmp_path: Path) -> None:
    """trusty-search and trusty-analyzer entries must never be modified."""
    mcp_path = _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "trusty-memory": {
                    "type": "stdio",
                    "command": "trusty-memory",
                    "args": ["serve", "--mcp"],
                },
                "trusty-search": {
                    "type": "stdio",
                    "command": "trusty-search",
                    "args": ["serve"],
                },
                "trusty-analyzer": {
                    "type": "stdio",
                    "command": "trusty-analyzer",
                    "args": ["mcp"],
                },
            }
        },
    )

    changed = mod.run_migration(project_dir=tmp_path)

    assert changed is True
    servers = json.loads(mcp_path.read_text())["mcpServers"]
    # Memory repaired...
    assert servers["trusty-memory"] == _BRIDGE_ENTRY
    # ...search and analyzer left exactly as they were.
    assert servers["trusty-search"] == {
        "type": "stdio",
        "command": "trusty-search",
        "args": ["serve"],
    }
    assert servers["trusty-analyzer"] == {
        "type": "stdio",
        "command": "trusty-analyzer",
        "args": ["mcp"],
    }


def test_idempotent_after_fix(tmp_path: Path) -> None:
    """Running twice: first run fixes, second run is a no-op."""
    _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "trusty-memory": {
                    "type": "stdio",
                    "command": "trusty-memory",
                    "args": ["serve", "--mcp"],
                }
            }
        },
    )

    assert mod.run_migration(project_dir=tmp_path) is True
    assert mod.run_migration(project_dir=tmp_path) is False
