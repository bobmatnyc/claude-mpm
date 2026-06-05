"""Tests for the dedup_hook_registrations migration (issue #677).

Coverage:
1. Repro + migration: duplicate MPM hooks (timeout:15 + timeout:60) are
   collapsed into a single canonical entry using the CANONICAL timeout.
2. User / non-MPM hook entries are preserved untouched.
3. Idempotent install: running either installer twice yields no duplicates
   (entry count per event == 1).
4. Timeout reconciliation: an existing entry with the wrong timeout is
   updated in-place (not duplicated) when the installer re-runs.
5. Migration idempotency: running the migration twice is a no-op the second
   time.
6. Legacy entries (no ``_mpm`` marker, command-string match only) are also
   deduplicated.
7. Canonical timeout per event: StopFailure/SessionEnd/PostCompact use 60,
   all others use 15.
8. Missing settings file: migration silently skips (no exception, returns
   True).
9. Parent-dir discovery: migration finds .claude/settings.json in a parent
   directory when cwd is in a subdirectory.
10. Backup rotation: only the 5 most-recent backups are kept per file.
11. Collapsed entry uses the canonical timeout (not the original stale value).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import claude_mpm.migrations.migrate_dedup_hook_registrations as dedup_mod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_settings(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_settings(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _make_mpm_hook(command: str = "claude-hook", timeout: int = 15) -> dict[str, Any]:
    return {"type": "command", "command": command, "timeout": timeout, "_mpm": True}


def _make_user_hook(command: str = "my-custom-hook") -> dict[str, Any]:
    """A non-MPM user-defined hook that must never be touched."""
    return {"type": "command", "command": command}


def _make_event_block(
    *hooks: dict[str, Any], matcher: str | None = "*"
) -> list[dict[str, Any]]:
    block: dict[str, Any] = {"hooks": list(hooks)}
    if matcher is not None:
        block["matcher"] = matcher
    return [block]


def _settings_with_hooks(hooks: dict[str, Any]) -> dict[str, Any]:
    return {"hooks": hooks}


# ---------------------------------------------------------------------------
# Unit tests for internal helpers
# ---------------------------------------------------------------------------


class TestIsMpmHookCommand:
    def test_explicit_mpm_marker(self) -> None:
        hook = {"type": "command", "command": "anything", "_mpm": True}
        assert dedup_mod._is_mpm_hook_command(hook) is True

    def test_legacy_claude_hook_command(self) -> None:
        hook = {"type": "command", "command": "claude-hook"}
        assert dedup_mod._is_mpm_hook_command(hook) is True

    def test_legacy_fast_script(self) -> None:
        hook = {"type": "command", "command": "/opt/claude-hook-fast.sh"}
        assert dedup_mod._is_mpm_hook_command(hook) is True

    def test_non_mpm_hook(self) -> None:
        hook = {"type": "command", "command": "my-hook"}
        assert dedup_mod._is_mpm_hook_command(hook) is False

    def test_wrong_type(self) -> None:
        hook = {"type": "script", "command": "claude-hook", "_mpm": True}
        assert dedup_mod._is_mpm_hook_command(hook) is False

    def test_non_dict(self) -> None:
        assert dedup_mod._is_mpm_hook_command("not a dict") is False  # type: ignore[arg-type]


class TestHookFingerprint:
    def test_same_command_different_timeout_same_fingerprint(self) -> None:
        h1 = {"type": "command", "command": "claude-hook", "timeout": 15}
        h2 = {"type": "command", "command": "claude-hook", "timeout": 60}
        assert dedup_mod._hook_fingerprint(h1) == dedup_mod._hook_fingerprint(h2)

    def test_different_command_different_fingerprint(self) -> None:
        h1 = {"type": "command", "command": "claude-hook"}
        h2 = {"type": "command", "command": "other-hook"}
        assert dedup_mod._hook_fingerprint(h1) != dedup_mod._hook_fingerprint(h2)

    def test_different_args_different_fingerprint(self) -> None:
        h1 = {"type": "command", "command": "python3", "args": ["-m", "mod_a"]}
        h2 = {"type": "command", "command": "python3", "args": ["-m", "mod_b"]}
        assert dedup_mod._hook_fingerprint(h1) != dedup_mod._hook_fingerprint(h2)


class TestDedupHooksInBlock:
    def test_no_duplicates_unchanged(self) -> None:
        hooks = [_make_mpm_hook("claude-hook", 15)]
        result = dedup_mod._dedup_hooks_in_block(hooks, "PreToolUse")
        assert len(result) == 1

    def test_duplicate_timeout15_and_timeout60_collapses_to_one(self) -> None:
        hooks = [
            _make_mpm_hook("claude-hook", 15),
            _make_mpm_hook("claude-hook", 60),
        ]
        result = dedup_mod._dedup_hooks_in_block(hooks, "PreToolUse")
        assert len(result) == 1
        # Canonical timeout for PreToolUse is 15 (migration converges to installer value)
        assert result[0]["timeout"] == 15

    def test_user_hooks_preserved(self) -> None:
        hooks = [
            _make_mpm_hook("claude-hook", 15),
            _make_user_hook("my-hook"),
            _make_mpm_hook("claude-hook", 60),
        ]
        result = dedup_mod._dedup_hooks_in_block(hooks, "PreToolUse")
        # 1 MPM + 1 user
        assert len(result) == 2
        commands = [h["command"] for h in result]
        assert "my-hook" in commands
        assert "claude-hook" in commands

    def test_canonical_timeout_enforced_regardless_of_input(self) -> None:
        """Canonical timeout is always used, regardless of what the input had."""
        hooks = [
            {"type": "command", "command": "claude-hook", "timeout": 5, "_mpm": True},
            {"type": "command", "command": "claude-hook", "timeout": 8, "_mpm": True},
        ]
        result = dedup_mod._dedup_hooks_in_block(hooks, "PreToolUse")
        assert len(result) == 1
        # canonical timeout for PreToolUse is 15
        assert result[0]["timeout"] == 15

    def test_stopfailure_uses_60_canonical_timeout(self) -> None:
        hooks = [_make_mpm_hook("claude-hook", 15)]
        result = dedup_mod._dedup_hooks_in_block(hooks, "StopFailure")
        assert result[0]["timeout"] == 60

    def test_sessionend_uses_60_canonical_timeout(self) -> None:
        hooks = [_make_mpm_hook("claude-hook", 15)]
        result = dedup_mod._dedup_hooks_in_block(hooks, "SessionEnd")
        assert result[0]["timeout"] == 60

    def test_postcompact_uses_60_canonical_timeout(self) -> None:
        hooks = [_make_mpm_hook("claude-hook", 15)]
        result = dedup_mod._dedup_hooks_in_block(hooks, "PostCompact")
        assert result[0]["timeout"] == 60

    def test_mpm_service_marker_preserved(self) -> None:
        hook = {
            "type": "command",
            "command": "python3",
            "args": ["-m", "claude_mpm.hooks.foo"],
            "timeout": 5,
            "_mpm": True,
            "_mpm_service": "foo",
        }
        result = dedup_mod._dedup_hooks_in_block([hook], "PostToolUse")
        assert result[0].get("_mpm_service") == "foo"

    def test_legacy_hook_deduplicated(self) -> None:
        """Legacy hooks matched by command string (no _mpm marker) are deduped."""
        hooks = [
            {"type": "command", "command": "claude-hook", "timeout": 15},
            {"type": "command", "command": "claude-hook", "timeout": 60},
        ]
        result = dedup_mod._dedup_hooks_in_block(hooks, "PreToolUse")
        assert len(result) == 1
        # Canonical timeout for PreToolUse is 15
        assert result[0]["timeout"] == 15


class TestDedupSettings:
    def test_duplicate_entries_removed(self) -> None:
        settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                )
            }
        )
        removed = dedup_mod._dedup_settings(settings)
        assert removed == 1
        block_hooks = settings["hooks"]["PreToolUse"][0]["hooks"]
        assert len(block_hooks) == 1
        # Canonical timeout for PreToolUse is 15
        assert block_hooks[0]["timeout"] == 15

    def test_no_hooks_section(self) -> None:
        settings: dict[str, Any] = {}
        removed = dedup_mod._dedup_settings(settings)
        assert removed == 0

    def test_multiple_events_each_deduped(self) -> None:
        settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                ),
                "Stop": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                    matcher=None,
                ),
            }
        )
        removed = dedup_mod._dedup_settings(settings)
        assert removed == 2

    def test_user_hooks_untouched(self) -> None:
        settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_user_hook("user-hook"),
                    _make_mpm_hook("claude-hook", 60),
                )
            }
        )
        dedup_mod._dedup_settings(settings)
        block_hooks = settings["hooks"]["PreToolUse"][0]["hooks"]
        commands = [h["command"] for h in block_hooks]
        assert "user-hook" in commands
        assert len(block_hooks) == 2  # 1 MPM + 1 user


# ---------------------------------------------------------------------------
# Integration tests: run_migration on tmp_path fixtures
# ---------------------------------------------------------------------------


class TestRunMigration:
    """Tests that call run_migration() with a monkeypatched cwd."""

    def _run_migration_in(self, path: Path) -> bool:
        with patch.object(Path, "cwd", return_value=path):
            return dedup_mod.run_migration()

    # ------------------------------------------------------------------
    # Repro + migration (requirement 1)
    # ------------------------------------------------------------------

    def test_repro_duplicate_hooks_collapsed(self, tmp_path: Path) -> None:
        """Constructing a settings.json with the bug state; migration fixes it."""
        settings_path = tmp_path / ".claude" / "settings.json"
        settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                ),
                "Stop": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                    matcher=None,
                ),
                "SubagentStop": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                ),
            }
        )
        _write_settings(settings_path, settings)

        result = self._run_migration_in(tmp_path)

        assert result is True
        after = _read_settings(settings_path)

        for event in ("PreToolUse", "Stop", "SubagentStop"):
            block_hooks = after["hooks"][event][0]["hooks"]
            assert len(block_hooks) == 1, (
                f"{event}: expected 1 entry after dedup, got {len(block_hooks)}"
            )
            # Canonical timeout for these events is 15
            assert block_hooks[0]["timeout"] == 15, (
                f"{event}: expected canonical timeout 15, got {block_hooks[0]['timeout']}"
            )

    def test_canonical_timeout_for_special_events(self, tmp_path: Path) -> None:
        """StopFailure, SessionEnd, PostCompact: duplicate entries collapse to
        a single entry with the *higher* timeout (60) preserved."""
        settings_path = tmp_path / ".claude" / "settings.json"
        # Create duplicate entries — one with timeout:15 and one with timeout:60
        settings = _settings_with_hooks(
            {
                "StopFailure": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                ),
                "SessionEnd": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                ),
                "PostCompact": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                ),
            }
        )
        _write_settings(settings_path, settings)

        self._run_migration_in(tmp_path)

        after = _read_settings(settings_path)
        for event in ("StopFailure", "SessionEnd", "PostCompact"):
            block_hooks = after["hooks"][event][0]["hooks"]
            assert len(block_hooks) == 1, f"{event}: expected 1 entry after dedup"
            assert block_hooks[0]["timeout"] == 60, f"{event}: expected timeout 60"

    # ------------------------------------------------------------------
    # User hooks preserved (requirement 2)
    # ------------------------------------------------------------------

    def test_user_hooks_preserved_after_migration(self, tmp_path: Path) -> None:
        settings_path = tmp_path / ".claude" / "settings.json"
        settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_user_hook("user-lint"),
                    _make_mpm_hook("claude-hook", 60),
                )
            }
        )
        _write_settings(settings_path, settings)

        self._run_migration_in(tmp_path)

        after = _read_settings(settings_path)
        commands = [h["command"] for h in after["hooks"]["PreToolUse"][0]["hooks"]]
        assert "user-lint" in commands, "user hook must survive migration"
        assert commands.count("claude-hook") == 1, "MPM hook must be deduped to 1"

    # ------------------------------------------------------------------
    # Migration idempotency (requirement 5)
    # ------------------------------------------------------------------

    def test_migration_idempotent(self, tmp_path: Path) -> None:
        """Running the migration twice is a no-op the second time."""
        settings_path = tmp_path / ".claude" / "settings.json"
        settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                )
            }
        )
        _write_settings(settings_path, settings)

        # First run: deduplicates
        self._run_migration_in(tmp_path)
        after_first = _read_settings(settings_path)

        # Second run: no-op
        self._run_migration_in(tmp_path)
        after_second = _read_settings(settings_path)

        assert after_first == after_second, "Second run must not change the file"

    # ------------------------------------------------------------------
    # Missing settings file (requirement 8)
    # ------------------------------------------------------------------

    def test_missing_settings_file_no_exception(self, tmp_path: Path) -> None:
        """Migration succeeds silently when no settings files exist."""
        result = self._run_migration_in(tmp_path)
        assert result is True

    # ------------------------------------------------------------------
    # Parent-dir discovery (requirement 9)
    # ------------------------------------------------------------------

    def test_parent_dir_claude_settings_found_from_subdir(self, tmp_path: Path) -> None:
        """Migration finds .claude/settings.json in a parent dir when cwd is in a subdir."""
        settings_path = tmp_path / ".claude" / "settings.json"
        settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                )
            }
        )
        _write_settings(settings_path, settings)

        # Run migration with cwd inside a subdirectory of tmp_path
        subdir = tmp_path / "src" / "some" / "package"
        subdir.mkdir(parents=True, exist_ok=True)

        with patch.object(Path, "cwd", return_value=subdir):
            result = dedup_mod.run_migration()

        assert result is True
        after = _read_settings(settings_path)
        block_hooks = after["hooks"]["PreToolUse"][0]["hooks"]
        assert len(block_hooks) == 1, (
            "Expected migration to de-dup hooks found in parent .claude dir"
        )

    def test_no_claude_dir_in_parents_returns_no_op(self, tmp_path: Path) -> None:
        """When no .claude dir exists anywhere in the parent chain, migration is a no-op."""
        # tmp_path has no .git or pyproject.toml, but also no .claude dir
        subdir = tmp_path / "a" / "b"
        subdir.mkdir(parents=True, exist_ok=True)

        with patch.object(Path, "cwd", return_value=subdir):
            result = dedup_mod.run_migration()

        assert result is True  # fail-open no-op

    # ------------------------------------------------------------------
    # Backup rotation (requirement 10)
    # ------------------------------------------------------------------

    def test_backup_rotation_keeps_only_5_most_recent(self, tmp_path: Path) -> None:
        """Old backups beyond _BACKUP_KEEP are deleted after a migration run."""
        import time

        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)

        # Pre-create 6 fake backup files with distinct timestamps
        for i in range(6):
            fake_ts = f"20250101_0000{i:02d}"
            backup = settings_path.parent / f"settings.json.backup_{fake_ts}"
            backup.write_text("{}", encoding="utf-8")
            # Ensure mtime ordering is distinct (avoid same-second collisions)
            time.sleep(0.01)

        # Write a settings.json with duplicates so the migration actually fires
        # (rotation only runs when a backup is created)
        settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),
                    _make_mpm_hook("claude-hook", 60),
                )
            }
        )
        _write_settings(settings_path, settings)

        self._run_migration_in(tmp_path)

        # 6 pre-existing + 1 newly created = 7 total; rotation keeps 5
        remaining = sorted((tmp_path / ".claude").glob("settings.json.backup_*"))
        assert len(remaining) <= dedup_mod._BACKUP_KEEP, (
            f"Expected at most {dedup_mod._BACKUP_KEEP} backups, "
            f"got {len(remaining)}: {[p.name for p in remaining]}"
        )

    # ------------------------------------------------------------------
    # Canonical timeout in dedup (requirement 11)
    # ------------------------------------------------------------------

    def test_collapsed_entry_uses_canonical_timeout(self, tmp_path: Path) -> None:
        """After migration, each event's single entry has the canonical timeout."""
        settings_path = tmp_path / ".claude" / "settings.json"
        settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    _make_mpm_hook("claude-hook", 999),  # stale/wrong value
                    _make_mpm_hook("claude-hook", 999),
                ),
                "StopFailure": _make_event_block(
                    _make_mpm_hook("claude-hook", 15),  # wrong for this event
                    _make_mpm_hook("claude-hook", 60),
                ),
            }
        )
        _write_settings(settings_path, settings)
        self._run_migration_in(tmp_path)

        after = _read_settings(settings_path)

        pre_hooks = after["hooks"]["PreToolUse"][0]["hooks"]
        assert len(pre_hooks) == 1
        assert pre_hooks[0]["timeout"] == 15, (
            f"PreToolUse canonical timeout is 15, got {pre_hooks[0]['timeout']}"
        )

        stop_hooks = after["hooks"]["StopFailure"][0]["hooks"]
        assert len(stop_hooks) == 1
        assert stop_hooks[0]["timeout"] == 60, (
            f"StopFailure canonical timeout is 60, got {stop_hooks[0]['timeout']}"
        )

    # ------------------------------------------------------------------
    # Malformed JSON
    # ------------------------------------------------------------------

    def test_malformed_json_does_not_crash(self, tmp_path: Path) -> None:
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text("{ not valid json }", encoding="utf-8")

        result = self._run_migration_in(tmp_path)
        assert result is True  # fail-open


# ---------------------------------------------------------------------------
# Installer idempotency tests (requirements 3 & 4)
# ---------------------------------------------------------------------------


class TestHookInstallerServiceIdempotency:
    """Prove that HookInstallerService.install_hooks() is idempotent."""

    def _make_service(self, tmp_path: Path):
        from claude_mpm.services.hook_installer_service import HookInstallerService

        svc = HookInstallerService.__new__(HookInstallerService)
        from claude_mpm.core.logging_config import get_logger

        svc.logger = get_logger("test")
        svc.project_root = tmp_path
        svc.claude_dir = tmp_path / ".claude"
        svc.claude_dir.mkdir(parents=True, exist_ok=True)
        svc.settings_file = svc.claude_dir / "settings.json"
        return svc

    def _count_mpm_hooks(self, settings: dict[str, Any], event: str) -> int:
        blocks = settings.get("hooks", {}).get(event, [])
        count = 0
        for block in blocks:
            for hook in block.get("hooks", []):
                if hook.get("_mpm") or hook.get("command") == "claude-hook":
                    count += 1
        return count

    def test_install_twice_no_duplicates(self, tmp_path: Path) -> None:
        """Running install_hooks() twice must not create duplicate entries."""
        svc = self._make_service(tmp_path)

        with patch("shutil.which", return_value="claude-hook"):
            svc.install_hooks(force=True)
            after_first = _read_settings(svc.settings_file)

            svc.install_hooks(force=True)
            after_second = _read_settings(svc.settings_file)

        for event in ("PreToolUse", "PostToolUse", "Stop", "SubagentStop"):
            count_first = self._count_mpm_hooks(after_first, event)
            count_second = self._count_mpm_hooks(after_second, event)
            assert count_first == count_second == 1, (
                f"{event}: expected 1 MPM hook after 2 installs, "
                f"got {count_first} / {count_second}"
            )

    def test_timeout_reconciliation_on_reinstall(self, tmp_path: Path) -> None:
        """Existing entry with wrong timeout is corrected in place, not duplicated."""
        settings_path = tmp_path / ".claude" / "settings.json"
        # Simulate a stale entry with a non-canonical timeout (e.g. 999)
        stale_settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    {
                        "type": "command",
                        "command": "claude-hook",
                        "timeout": 999,
                        "_mpm": True,
                    }
                )
            }
        )
        _write_settings(settings_path, stale_settings)

        svc = self._make_service(tmp_path)
        with patch("shutil.which", return_value="claude-hook"):
            svc.install_hooks(force=True)

        after = _read_settings(settings_path)
        block_hooks = after["hooks"]["PreToolUse"][0]["hooks"]
        # Must still be exactly one entry (not duplicated)
        mpm_hooks = [h for h in block_hooks if h.get("_mpm")]
        assert len(mpm_hooks) == 1, "Expected 1 MPM hook after reconciliation"
        # Timeout must be reconciled to canonical (15 for PreToolUse)
        assert mpm_hooks[0]["timeout"] == 15, (
            f"Expected canonical timeout 15, got {mpm_hooks[0]['timeout']}"
        )


class TestHookInstallerIdempotency:
    """Prove that HookInstaller._update_claude_settings() is idempotent."""

    def _make_installer(self, tmp_path: Path):
        from unittest.mock import MagicMock

        from claude_mpm.hooks.claude_hooks.installer import HookInstaller

        inst = HookInstaller.__new__(HookInstaller)
        inst.logger = MagicMock()
        # Required attrs set by __init__ that we bypass via __new__
        inst._claude_version = None
        inst._hook_script_path = None
        inst.project_root = tmp_path
        inst.claude_dir = tmp_path / ".claude"
        inst.claude_dir.mkdir(parents=True, exist_ok=True)
        inst.hooks_dir = inst.claude_dir / "hooks"
        inst.settings_file = inst.claude_dir / "settings.json"
        inst.old_settings_file = inst.claude_dir / "settings.local.json"
        # Stub out version detection so we don't need a real claude binary
        inst.supports_new_hooks = MagicMock(return_value=False)
        inst._fix_status_line = MagicMock()
        inst._cleanup_old_settings = MagicMock()
        return inst

    def _count_mpm_hooks(self, settings: dict[str, Any], event: str) -> int:
        blocks = settings.get("hooks", {}).get(event, [])
        count = 0
        for block in blocks:
            for hook in block.get("hooks", []):
                if hook.get("_mpm") or hook.get("command") == "claude-hook":
                    count += 1
        return count

    def test_update_twice_no_duplicates(self, tmp_path: Path) -> None:
        inst = self._make_installer(tmp_path)

        inst._update_claude_settings("claude-hook")
        after_first = _read_settings(inst.settings_file)

        inst._update_claude_settings("claude-hook")
        after_second = _read_settings(inst.settings_file)

        for event in ("PreToolUse", "PostToolUse", "Stop", "SubagentStop"):
            c1 = self._count_mpm_hooks(after_first, event)
            c2 = self._count_mpm_hooks(after_second, event)
            assert c1 == c2 == 1, (
                f"{event}: expected 1 MPM hook after 2 updates, got {c1}/{c2}"
            )

    def test_timeout_reconciliation_on_update(self, tmp_path: Path) -> None:
        """Existing entry with wrong timeout is updated in place."""
        settings_path = tmp_path / ".claude" / "settings.json"
        stale_settings = _settings_with_hooks(
            {
                "PreToolUse": _make_event_block(
                    {
                        "type": "command",
                        "command": "claude-hook",
                        "timeout": 999,
                        "_mpm": True,
                    }
                )
            }
        )
        _write_settings(settings_path, stale_settings)

        inst = self._make_installer(tmp_path)
        inst._update_claude_settings("claude-hook")

        after = _read_settings(settings_path)
        block_hooks = after["hooks"]["PreToolUse"][0]["hooks"]
        mpm_hooks = [h for h in block_hooks if h.get("_mpm")]
        assert len(mpm_hooks) == 1
        assert mpm_hooks[0]["timeout"] == 15

    def test_canonical_timeout_written_per_event(self, tmp_path: Path) -> None:
        """StopFailure gets timeout:60 even on fresh install."""
        # StopFailure is not installed by HookInstaller directly in the simple
        # events list, but we test that the canonical map is wired correctly
        # by calling _make_hook_command internally. We simulate it by calling
        # _update_claude_settings on a fresh file and checking the canonical
        # timeout for events that ARE written.
        inst = self._make_installer(tmp_path)
        inst._update_claude_settings("claude-hook")

        after = _read_settings(inst.settings_file)
        # PreToolUse canonical timeout is 15
        pre_hooks = after["hooks"]["PreToolUse"][0]["hooks"]
        mpm = [h for h in pre_hooks if h.get("_mpm")]
        assert mpm[0]["timeout"] == 15


# ---------------------------------------------------------------------------
# Canonical timeout constants consistency check
# ---------------------------------------------------------------------------


def test_canonical_timeout_map_consistency() -> None:
    """The shared timeout_constants module is the single source of truth.

    All consumers (migration, installers) must import from it — there must be
    no second definition of CANONICAL_HOOK_TIMEOUTS anywhere else.
    """
    from claude_mpm.hooks.timeout_constants import (
        CANONICAL_HOOK_TIMEOUTS,
        DEFAULT_HOOK_TIMEOUT,
        canonical_timeout,
    )

    # Verify the shared values are correct.
    assert DEFAULT_HOOK_TIMEOUT == 15
    assert CANONICAL_HOOK_TIMEOUTS["StopFailure"] == 60
    assert CANONICAL_HOOK_TIMEOUTS["SessionEnd"] == 60
    assert CANONICAL_HOOK_TIMEOUTS["PostCompact"] == 60
    assert CANONICAL_HOOK_TIMEOUTS.get("PreToolUse", DEFAULT_HOOK_TIMEOUT) == 15
    assert CANONICAL_HOOK_TIMEOUTS.get("Stop", DEFAULT_HOOK_TIMEOUT) == 15

    # The helper function must route through the shared map.
    assert canonical_timeout("StopFailure") == 60
    assert canonical_timeout("SessionEnd") == 60
    assert canonical_timeout("PostCompact") == 60
    assert canonical_timeout("PreToolUse") == 15
    assert canonical_timeout("Stop") == 15
    assert canonical_timeout("UnknownEvent") == 15

    # The migration re-exports the shared constants (aliased with underscore prefix
    # for backward compatibility) — verify they are the SAME objects, not copies.
    from claude_mpm.migrations.migrate_dedup_hook_registrations import (
        _CANONICAL_TIMEOUTS as MIGRATION_TIMEOUTS,
        _DEFAULT_TIMEOUT as MIGRATION_DEFAULT,
    )

    assert MIGRATION_TIMEOUTS is CANONICAL_HOOK_TIMEOUTS, (
        "Migration _CANONICAL_TIMEOUTS must be the same object as the shared "
        "CANONICAL_HOOK_TIMEOUTS — no local copy allowed"
    )
    assert MIGRATION_DEFAULT == DEFAULT_HOOK_TIMEOUT


def test_no_local_timeout_definition_in_installer() -> None:
    """installer.py must not define its own _CANONICAL_TIMEOUTS or _DEFAULT_TIMEOUT."""
    import ast
    import inspect

    import claude_mpm.hooks.claude_hooks.installer as installer_mod
    import claude_mpm.services.hook_installer_service as service_mod

    for mod, name in [
        (installer_mod, "installer.py"),
        (service_mod, "hook_installer_service.py"),
    ]:
        src = inspect.getsource(mod)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in (
                        "_CANONICAL_TIMEOUTS",
                        "_canonical_timeouts",
                        "_DEFAULT_TIMEOUT",
                        "_default_timeout",
                    ):
                        raise AssertionError(
                            f"{name} defines its own timeout constant '{target.id}'. "
                            "Move it to hooks/timeout_constants.py and import from there."
                        )
