"""Tests for the trusty-search / trusty-memory autodetect migration.

These tests deliberately mock both ``shutil.which`` and the HTTP health probe
so they never depend on a real daemon being installed on the test runner.
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - used at runtime in fixtures & call sites
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest

from claude_mpm.migrations import migrate_trusty_autodetect as mod


def _make_which(installed: set[str]) -> Callable[[str], str | None]:
    """Return a ``shutil.which`` stand-in matching the given binary set."""

    def fake_which(name: str) -> str | None:
        return f"/fake/bin/{name}" if name in installed else None

    return fake_which


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Empty project directory (no pre-existing .mcp.json)."""
    return tmp_path


def test_writes_entries_when_both_daemons_healthy(project_dir: Path) -> None:
    """Both binaries on PATH + both daemons healthy → both entries written."""
    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which({"trusty-search", "trusty-memory"}),
        ),
        patch.object(mod, "_http_health_check", return_value=True),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is True

    mcp_json = project_dir / ".mcp.json"
    assert mcp_json.exists()

    config = json.loads(mcp_json.read_text())
    servers = config["mcpServers"]

    assert servers["trusty-search"] == {
        "type": "stdio",
        "command": "trusty-search",
        "args": ["serve"],
    }
    assert servers["trusty-memory"] == {
        "type": "stdio",
        "command": "trusty-memory",
        "args": ["serve", "--mcp"],
    }


def test_no_op_when_daemons_not_running(project_dir: Path) -> None:
    """Binary present but health probe fails → no file written, no exception."""
    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which({"trusty-search", "trusty-memory"}),
        ),
        patch.object(mod, "_http_health_check", return_value=False),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is False
    assert not (project_dir / ".mcp.json").exists()


def test_no_op_when_binaries_missing(project_dir: Path) -> None:
    """No binary on PATH → skip without probing HTTP."""
    probe_called = []

    def tracking_probe(url: str, _timeout: float = 2.0) -> bool:
        probe_called.append(url)
        return True

    with (
        patch.object(mod.shutil, "which", side_effect=_make_which(set())),
        patch.object(mod, "_http_health_check", side_effect=tracking_probe),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is False
    assert probe_called == [], "Health probe should be skipped when binary missing"
    assert not (project_dir / ".mcp.json").exists()


def test_idempotent_when_entries_already_present(project_dir: Path) -> None:
    """Existing entries → migration is a no-op and returns False."""
    existing = {
        "mcpServers": {
            "trusty-search": {
                "type": "stdio",
                "command": "trusty-search",
                "args": ["serve"],
            },
            "trusty-memory": {
                "type": "stdio",
                "command": "trusty-memory",
                "args": ["serve", "--mcp"],
            },
        }
    }
    mcp_path = project_dir / ".mcp.json"
    mcp_path.write_text(json.dumps(existing, indent=2) + "\n")
    original_contents = mcp_path.read_text()

    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which({"trusty-search", "trusty-memory"}),
        ),
        patch.object(mod, "_http_health_check", return_value=True),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is False
    # File untouched.
    assert mcp_path.read_text() == original_contents


def test_partial_injection_preserves_unrelated_entries(project_dir: Path) -> None:
    """Only the missing daemon is added; unrelated MCP servers stay intact."""
    existing = {
        "mcpServers": {
            "trusty-search": {
                "type": "stdio",
                "command": "trusty-search",
                "args": ["serve"],
            },
            "some-other-server": {"type": "stdio", "command": "whatever"},
        }
    }
    mcp_path = project_dir / ".mcp.json"
    mcp_path.write_text(json.dumps(existing, indent=2) + "\n")

    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which({"trusty-search", "trusty-memory"}),
        ),
        patch.object(mod, "_http_health_check", return_value=True),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is True
    config = json.loads(mcp_path.read_text())
    servers = config["mcpServers"]
    assert "trusty-memory" in servers
    assert "trusty-search" in servers
    # Pre-existing unrelated entry must survive.
    assert servers["some-other-server"] == {"type": "stdio", "command": "whatever"}
