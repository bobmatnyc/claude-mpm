"""
Tests for migration runner stdout/logging behavior (issue #595).

The corrective "scan-and-repair-if-present" migrations (e.g.
``fix_mcp_command_args``, ``fix_trusty_memory_bridge``) return ``False`` on a
clean system and are re-run on every launch. They must NOT print noise on a
no-op. Output is only expected when a migration actually APPLIES a change
(``run()`` returns ``True``). Genuine errors (``run()`` raises) must remain
visible.
"""

from unittest.mock import patch

import pytest

from claude_mpm.migrations import runner
from claude_mpm.migrations.registry import Migration


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """Point the runner's STATE_FILE at a temp location so completion tracking
    does not touch the real ~/.claude-mpm/migrations.json."""
    state_file = tmp_path / "migrations.json"
    monkeypatch.setattr(runner, "STATE_FILE", state_file)
    return state_file


def _run_with_migrations(migrations):
    """Run the runner with a patched MIGRATIONS list and capture nothing else."""
    with patch.object(runner, "MIGRATIONS", migrations):
        return runner.run_pending_migrations(current_version="test")


def test_noop_migration_produces_no_stdout(isolated_state, capsys):
    """A migration returning False (clean no-op) must print nothing."""
    noop = Migration(
        id="noop_clean_scan",
        version="6.4.0",
        description="Fix MCP server configs where command contains spaces",
        run=lambda: False,
    )

    count = _run_with_migrations([noop])

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "skipped" not in captured.out
    assert "🔄" not in captured.out
    assert count == 0


def test_applied_migration_prints_applied_line(isolated_state, capsys):
    """A migration returning True (applied) still prints its applied line."""
    applied = Migration(
        id="applied_migration",
        version="6.4.0",
        description="Repair broken trusty-memory MCP entries",
        run=lambda: True,
    )

    count = _run_with_migrations([applied])

    captured = capsys.readouterr()
    assert "Migration applied: Repair broken trusty-memory MCP entries" in captured.out
    assert "✅ Migration complete: applied_migration" in captured.out
    assert count == 1


def test_exception_is_still_surfaced(isolated_state, capsys):
    """A migration that raises must still be surfaced on stdout (not silenced)."""

    def boom() -> bool:
        raise RuntimeError("kaboom")

    failing = Migration(
        id="failing_migration",
        version="6.4.0",
        description="Migration that explodes",
        run=boom,
    )

    count = _run_with_migrations([failing])

    captured = capsys.readouterr()
    assert "❌ Migration failed: failing_migration" in captured.out
    assert "kaboom" in captured.out
    # Exception path does not count as an applied migration.
    assert count == 0


def test_noop_logs_debug_not_warning(isolated_state, caplog):
    """No-op path downgrades to a debug trace (no user-facing warning)."""
    import logging

    noop = Migration(
        id="noop_debug",
        version="6.4.0",
        description="Clean scan no-op",
        run=lambda: False,
    )

    with caplog.at_level(logging.DEBUG, logger=runner.logger.name):
        _run_with_migrations([noop])

    debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("no-op" in r.getMessage() for r in debug_records)
    assert warning_records == []
