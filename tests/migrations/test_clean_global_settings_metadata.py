"""Tests for the clean_global_settings_metadata migration (issue #676).

Coverage:
1. Strips ``_mpm_managed`` and ``_mpm_version`` keys; preserves spinner keys,
   ``_mpm_spinner_version``, and unrelated user keys.
2. Removes MPM hook remnants (entries with ``_mpm: true`` or a ``command``
   containing ``"claude-hook"`` / other MPM markers) while preserving user hooks.
3. Idempotent: running the migration a second time is a no-op (returns True,
   no further writes, count unchanged).
4. No-op when none of the stale keys are present.
5. No-op when ``~/.claude/settings.json`` does not exist.
6. Empty ``hooks`` dict is removed after all MPM entries are stripped.
7. Legacy hook entries (no ``_mpm`` marker; matched by command-string substring)
   are also removed.
8. ``_mpm_spinner_version`` is NOT removed (it is a spinner key, not stale
   metadata).

IMPORTANT: Tests use a tmp-file path injected via ``unittest.mock.patch``; the
real ``~/.claude/settings.json`` is NEVER touched.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import claude_mpm.migrations.migrate_clean_global_settings_metadata as migration_mod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _mpm_hook(command: str = "claude-hook") -> dict[str, Any]:
    return {"type": "command", "command": command, "_mpm": True}


def _user_hook(command: str = "my-custom-tool") -> dict[str, Any]:
    """A user-authored hook that must never be removed."""
    return {"type": "command", "command": command}


def _event_block(*hooks: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"matcher": "*", "hooks": list(hooks)}]


def _run(settings_path: Path) -> bool:
    """Invoke the migration with its global-settings path redirected to ``settings_path``."""
    with patch.object(
        Path,
        "home",
        return_value=settings_path.parent.parent,  # parent of .claude/
    ):
        return migration_mod.run_migration()


# ---------------------------------------------------------------------------
# Unit tests: _is_mpm_hook_command
# ---------------------------------------------------------------------------


class TestIsMpmHookCommand:
    def test_explicit_mpm_marker(self) -> None:
        hook = {"type": "command", "command": "anything", "_mpm": True}
        assert migration_mod._is_mpm_hook_command(hook) is True

    def test_claude_hook_command_string(self) -> None:
        hook = {"type": "command", "command": "claude-hook"}
        assert migration_mod._is_mpm_hook_command(hook) is True

    def test_claude_hook_fast_path(self) -> None:
        hook = {"type": "command", "command": "/opt/claude-hook-fast.sh"}
        assert migration_mod._is_mpm_hook_command(hook) is True

    def test_claude_hook_in_args(self) -> None:
        hook = {"type": "command", "command": "python", "args": ["claude-hook"]}
        assert migration_mod._is_mpm_hook_command(hook) is True

    def test_user_hook_not_matched(self) -> None:
        hook = {"type": "command", "command": "my-hook"}
        assert migration_mod._is_mpm_hook_command(hook) is False

    def test_non_dict_returns_false(self) -> None:
        assert migration_mod._is_mpm_hook_command("string") is False  # type: ignore[arg-type]
        assert migration_mod._is_mpm_hook_command(None) is False  # type: ignore[arg-type]

    def test_claude_mpm_substring_in_command_not_matched(self) -> None:
        """A command that merely *contains* 'claude_mpm' as a substring is NOT removed.

        Only hooks whose basename exactly matches a known MPM script, or whose
        path contains the '/claude_mpm/' path component, are removed.
        A bare substring like '/usr/bin/claude_mpm_wrapper' must be preserved.
        """
        hook = {"type": "command", "command": "/usr/bin/claude_mpm_wrapper"}
        assert migration_mod._is_mpm_hook_command(hook) is False

    def test_claude_mpm_path_component_is_matched(self) -> None:
        """A command whose path contains '/claude_mpm/' IS removed (package path)."""
        hook = {"type": "command", "command": "/opt/lib/claude_mpm/hooks/handler.sh"}
        assert migration_mod._is_mpm_hook_command(hook) is True


# ---------------------------------------------------------------------------
# Unit tests: _strip_stale_metadata
# ---------------------------------------------------------------------------


class TestStripStaleMetadata:
    def test_removes_mpm_managed(self) -> None:
        settings: dict[str, Any] = {"_mpm_managed": True, "theme": "dark"}
        result, count = migration_mod._strip_stale_metadata(settings)
        assert "_mpm_managed" not in result
        assert result["theme"] == "dark"
        assert count == 1

    def test_removes_mpm_version(self) -> None:
        settings: dict[str, Any] = {"_mpm_version": "6.3.0", "envs": {}}
        result, count = migration_mod._strip_stale_metadata(settings)
        assert "_mpm_version" not in result
        assert "envs" in result
        assert count == 1

    def test_removes_both_metadata_keys(self) -> None:
        settings: dict[str, Any] = {
            "_mpm_managed": True,
            "_mpm_version": "6.0.0",
            "user_key": "keep",
        }
        result, count = migration_mod._strip_stale_metadata(settings)
        assert "_mpm_managed" not in result
        assert "_mpm_version" not in result
        assert result["user_key"] == "keep"
        assert count == 2

    def test_preserves_spinner_keys(self) -> None:
        settings: dict[str, Any] = {
            "_mpm_managed": True,
            "_mpm_version": "6.0.0",
            "spinnerVerbs": ["coding"],
            "spinnerTipsEnabled": True,
            "spinnerTipsOverride": [],
            "_mpm_spinner_version": "6.5.0",
        }
        result, count = migration_mod._strip_stale_metadata(settings)
        assert "spinnerVerbs" in result
        assert "spinnerTipsEnabled" in result
        assert "spinnerTipsOverride" in result
        assert "_mpm_spinner_version" in result
        assert count == 2

    def test_no_stale_keys_returns_zero(self) -> None:
        settings: dict[str, Any] = {"theme": "dark"}
        _, count = migration_mod._strip_stale_metadata(settings)
        assert count == 0

    def test_removes_mpm_hooks_preserves_user_hooks(self) -> None:
        settings: dict[str, Any] = {
            "hooks": {
                "PreToolUse": _event_block(_mpm_hook(), _user_hook()),
            }
        }
        result, count = migration_mod._strip_stale_metadata(settings)
        hooks = result["hooks"]["PreToolUse"][0]["hooks"]
        assert len(hooks) == 1
        assert hooks[0]["command"] == "my-custom-tool"
        assert count == 1

    def test_empty_hooks_key_removed(self) -> None:
        settings: dict[str, Any] = {
            "hooks": {
                "PreToolUse": _event_block(_mpm_hook()),
            }
        }
        result, count = migration_mod._strip_stale_metadata(settings)
        assert "hooks" not in result
        assert count == 1

    def test_legacy_hook_removed_by_command_string(self) -> None:
        """Hooks without ``_mpm`` marker but matching command string are removed."""
        legacy_hook = {"type": "command", "command": "claude-hook-fast.sh"}
        settings: dict[str, Any] = {
            "hooks": {
                "PostToolUse": _event_block(legacy_hook),
            }
        }
        result, count = migration_mod._strip_stale_metadata(settings)
        assert "hooks" not in result
        assert count == 1

    def test_multiple_events_all_cleaned(self) -> None:
        settings: dict[str, Any] = {
            "_mpm_managed": True,
            "hooks": {
                "PreToolUse": _event_block(_mpm_hook()),
                "PostToolUse": _event_block(_mpm_hook(), _user_hook()),
            },
        }
        result, count = migration_mod._strip_stale_metadata(settings)
        assert "_mpm_managed" not in result
        # PreToolUse block was completely MPM → entire hooks key for that event removed
        assert "PreToolUse" not in result.get("hooks", {})
        # PostToolUse still has the user hook
        post = result["hooks"]["PostToolUse"][0]["hooks"]
        assert len(post) == 1
        assert post[0]["command"] == "my-custom-tool"
        # 1 metadata key + 1 MPM hook in PreToolUse + 1 MPM hook in PostToolUse
        assert count == 3


# ---------------------------------------------------------------------------
# Integration tests: run_migration (uses tmp path, never touches real fs)
# ---------------------------------------------------------------------------


class TestRunMigration:
    def test_strips_metadata_and_preserves_user_and_spinner_keys(
        self, tmp_path: Path
    ) -> None:
        settings_file = tmp_path / ".claude" / "settings.json"
        _write(
            settings_file,
            {
                "_mpm_managed": True,
                "_mpm_version": "6.3.0",
                "spinnerVerbs": ["coding"],
                "spinnerTipsEnabled": True,
                "_mpm_spinner_version": "6.3.0",
                "theme": "dark",
                "user_setting": 42,
            },
        )

        result = _run(settings_file)

        assert result is True
        data = _read(settings_file)
        assert "_mpm_managed" not in data
        assert "_mpm_version" not in data
        # Spinner keys preserved
        assert data["spinnerVerbs"] == ["coding"]
        assert data["spinnerTipsEnabled"] is True
        assert data["_mpm_spinner_version"] == "6.3.0"
        # User keys preserved
        assert data["theme"] == "dark"
        assert data["user_setting"] == 42

    def test_removes_mpm_hooks_preserves_user_hooks(self, tmp_path: Path) -> None:
        settings_file = tmp_path / ".claude" / "settings.json"
        _write(
            settings_file,
            {
                "_mpm_managed": True,
                "hooks": {
                    "PreToolUse": _event_block(_mpm_hook(), _user_hook("my-linter")),
                    "PostToolUse": _event_block(_mpm_hook()),
                },
            },
        )

        result = _run(settings_file)

        assert result is True
        data = _read(settings_file)
        assert "_mpm_managed" not in data
        # PostToolUse was all-MPM → removed
        assert "PostToolUse" not in data.get("hooks", {})
        # PreToolUse still has the user hook
        pre_hooks = data["hooks"]["PreToolUse"][0]["hooks"]
        assert len(pre_hooks) == 1
        assert pre_hooks[0]["command"] == "my-linter"

    def test_idempotent_second_run_noop(self, tmp_path: Path) -> None:
        settings_file = tmp_path / ".claude" / "settings.json"
        _write(
            settings_file,
            {
                "_mpm_managed": True,
                "_mpm_version": "6.0.0",
                "theme": "dark",
            },
        )

        _run(settings_file)
        content_after_first = settings_file.read_text()

        _run(settings_file)
        content_after_second = settings_file.read_text()

        # Content must be identical on the second run
        assert content_after_first == content_after_second

    def test_noop_when_no_stale_keys(self, tmp_path: Path) -> None:
        settings_file = tmp_path / ".claude" / "settings.json"
        _write(
            settings_file,
            {
                "theme": "dark",
                "spinnerVerbs": ["coding"],
                "_mpm_spinner_version": "6.5.0",
            },
        )
        original_content = settings_file.read_text()

        result = _run(settings_file)

        assert result is True
        # File must be unchanged
        assert settings_file.read_text() == original_content

    def test_noop_when_file_missing(self, tmp_path: Path) -> None:
        settings_file = tmp_path / ".claude" / "settings.json"
        # File does not exist
        assert not settings_file.exists()

        result = _run(settings_file)

        assert result is True
        assert not settings_file.exists()

    def test_legacy_hooks_removed_by_command_string(self, tmp_path: Path) -> None:
        """MPM hooks written before the ``_mpm`` marker are identified by command string."""
        legacy_hook = {"type": "command", "command": "claude-hook-fast.sh"}
        settings_file = tmp_path / ".claude" / "settings.json"
        _write(
            settings_file,
            {
                "hooks": {
                    "PreToolUse": _event_block(legacy_hook, _user_hook()),
                }
            },
        )

        result = _run(settings_file)

        assert result is True
        data = _read(settings_file)
        pre_hooks = data["hooks"]["PreToolUse"][0]["hooks"]
        assert len(pre_hooks) == 1
        assert pre_hooks[0]["command"] == "my-custom-tool"

    def test_user_hook_with_claude_mpm_substring_preserved(
        self, tmp_path: Path
    ) -> None:
        """A user hook whose command merely CONTAINS 'claude_mpm' is NOT removed.

        This is the critical false-positive regression test: commands like
        '/usr/local/bin/claude_mpm_wrapper' or 'pre_claude_mpm_check.sh' must
        survive the migration unchanged.  Only hooks with ``_mpm: true`` or
        whose basename/path-component precisely matches a known MPM script are
        removed.
        """
        user_hook_with_mpm_in_name = {
            "type": "command",
            "command": "/usr/local/bin/claude_mpm_wrapper",
        }
        settings_file = tmp_path / ".claude" / "settings.json"
        _write(
            settings_file,
            {
                "_mpm_managed": True,
                "hooks": {
                    "PreToolUse": _event_block(
                        _mpm_hook(),  # real MPM hook — should be removed
                        user_hook_with_mpm_in_name,  # user hook — must survive
                    ),
                },
            },
        )

        result = _run(settings_file)

        assert result is True
        data = _read(settings_file)
        assert "_mpm_managed" not in data
        pre_hooks = data["hooks"]["PreToolUse"][0]["hooks"]
        assert len(pre_hooks) == 1, (
            "Expected user hook to survive; MPM hook should have been removed"
        )
        assert pre_hooks[0]["command"] == "/usr/local/bin/claude_mpm_wrapper"

    def test_mpm_spinner_version_not_removed(self, tmp_path: Path) -> None:
        """``_mpm_spinner_version`` must not be treated as a stale metadata key."""
        settings_file = tmp_path / ".claude" / "settings.json"
        _write(
            settings_file,
            {
                "_mpm_managed": True,
                "_mpm_version": "6.0.0",
                "_mpm_spinner_version": "6.5.0",
            },
        )

        _run(settings_file)

        data = _read(settings_file)
        assert "_mpm_managed" not in data
        assert "_mpm_version" not in data
        assert "_mpm_spinner_version" in data
        assert data["_mpm_spinner_version"] == "6.5.0"

    def test_backup_created_when_changes_made(self, tmp_path: Path) -> None:
        settings_file = tmp_path / ".claude" / "settings.json"
        _write(settings_file, {"_mpm_managed": True})

        _run(settings_file)

        backups = list((tmp_path / ".claude").glob("settings.json.backup_*"))
        assert len(backups) == 1

    def test_no_backup_when_no_changes(self, tmp_path: Path) -> None:
        settings_file = tmp_path / ".claude" / "settings.json"
        _write(settings_file, {"theme": "dark"})

        _run(settings_file)

        backups = list((tmp_path / ".claude").glob("settings.json.backup_*"))
        assert len(backups) == 0

    def test_returns_true_on_invalid_json(self, tmp_path: Path) -> None:
        """Migration must be fail-open even with malformed JSON."""
        settings_file = tmp_path / ".claude" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text("{ invalid json }", encoding="utf-8")

        result = _run(settings_file)

        assert result is True
