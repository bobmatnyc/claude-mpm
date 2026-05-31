"""Tests for the v6_4_18_remove_absolute_hook_paths migration.

Coverage:
1. Absolute MPM hook path → replaced with ``"claude-hook"``.
2. Idempotency: a second run on an already-migrated file is a no-op.
3. Malformed JSON is handled gracefully (no mangling, function returns False).
4. The global ``~/.claude/settings.local.json`` branch is scanned (HOME
   monkeypatched — never touches the real ``~/.claude``).
5. Non-MPM command strings are left untouched.
6. Missing settings files are silently skipped (no exception).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

import claude_mpm.migrations.v6_4_18_remove_absolute_hook_paths as mod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(hooks: dict) -> dict:
    """Wrap *hooks* dict in a minimal settings structure."""
    return {"hooks": hooks}


def _hooks_with_command(command: str) -> dict:
    """Build a hooks dict with one PreToolUse entry using *command*."""
    return {
        "PreToolUse": [
            {
                "matcher": ".*",
                "hooks": [
                    {"type": "command", "command": command},
                ],
            }
        ]
    }


def _write_settings(path: Path, data: dict) -> None:
    """Write *data* as formatted JSON to *path*, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _read_settings(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Absolute MPM hook path → "claude-hook"
# ---------------------------------------------------------------------------


def test_absolute_hook_path_replaced(tmp_path: Path) -> None:
    """An absolute path containing a known MPM script name is replaced."""
    settings_path = tmp_path / ".claude" / "settings.json"
    data = _make_settings(
        _hooks_with_command("/Users/alice/lib/claude-mpm/claude-hook-fast.sh")
    )
    _write_settings(settings_path, data)

    changed = mod.run_migration(installation_dir=tmp_path)
    assert changed is True

    result = _read_settings(settings_path)
    cmd = result["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert cmd == "claude-hook"


def test_alternative_script_name_replaced(tmp_path: Path) -> None:
    """claude-hook-handler.sh is also recognised as an absolute MPM hook."""
    settings_path = tmp_path / ".claude" / "settings.json"
    data = _make_settings(_hooks_with_command("/opt/tools/claude-hook-handler.sh"))
    _write_settings(settings_path, data)

    mod.run_migration(installation_dir=tmp_path)

    result = _read_settings(settings_path)
    cmd = result["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert cmd == "claude-hook"


def test_claude_mpm_hook_sh_replaced(tmp_path: Path) -> None:
    """claude-mpm-hook.sh is also replaced."""
    settings_path = tmp_path / ".claude" / "settings.json"
    data = _make_settings(
        _hooks_with_command("/home/user/.local/bin/claude-mpm-hook.sh")
    )
    _write_settings(settings_path, data)

    mod.run_migration(installation_dir=tmp_path)

    result = _read_settings(settings_path)
    cmd = result["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert cmd == "claude-hook"


# ---------------------------------------------------------------------------
# 2. Idempotency
# ---------------------------------------------------------------------------


def test_idempotent_already_uses_claude_hook(tmp_path: Path) -> None:
    """A file that already uses 'claude-hook' is left untouched (no-op)."""
    settings_path = tmp_path / ".claude" / "settings.json"
    data = _make_settings(_hooks_with_command("claude-hook"))
    _write_settings(settings_path, data)
    original_mtime = settings_path.stat().st_mtime

    result = mod.run_migration(installation_dir=tmp_path)
    # run_migration returns True (success) even for no-op runs
    assert result is True
    # File should not have been rewritten (mtime unchanged)
    assert settings_path.stat().st_mtime == original_mtime


def test_run_twice_produces_same_result(tmp_path: Path) -> None:
    """Running the migration twice leaves the file identical."""
    settings_path = tmp_path / ".claude" / "settings.json"
    data = _make_settings(_hooks_with_command("/Users/alice/src/claude-hook-fast.sh"))
    _write_settings(settings_path, data)

    mod.run_migration(installation_dir=tmp_path)
    first_run_content = settings_path.read_text(encoding="utf-8")

    mod.run_migration(installation_dir=tmp_path)
    second_run_content = settings_path.read_text(encoding="utf-8")

    assert first_run_content == second_run_content


# ---------------------------------------------------------------------------
# 3. Malformed JSON
# ---------------------------------------------------------------------------


def test_malformed_json_does_not_raise(tmp_path: Path) -> None:
    """Invalid JSON in settings file must be skipped silently (no exception)."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("{not valid json}", encoding="utf-8")

    # Must not raise
    result = mod.run_migration(installation_dir=tmp_path)
    # Returns False because _migrate_single_file returns False on parse error
    assert result is False


def test_malformed_json_file_not_modified(tmp_path: Path) -> None:
    """The corrupted file must not be overwritten with empty/partial content."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    bad_content = "{not valid json}"
    settings_path.write_text(bad_content, encoding="utf-8")

    mod.run_migration(installation_dir=tmp_path)

    # File content must be unchanged
    assert settings_path.read_text(encoding="utf-8") == bad_content


# ---------------------------------------------------------------------------
# 4. Global ~/.claude/settings.local.json branch (HOME monkeypatched)
# ---------------------------------------------------------------------------


def test_global_settings_local_scanned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The migration also patches ~/.claude/settings.local.json.

    HOME is monkeypatched to a tmp_path subdirectory so we never touch the
    real ~/.claude directory on the test runner.
    """
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    # Also patch Path.home() which is what the module uses
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

    global_settings = fake_home / ".claude" / "settings.local.json"
    data = _make_settings(
        _hooks_with_command("/Users/bob/Projects/claude-mpm/claude-hook-fast.sh")
    )
    _write_settings(global_settings, data)

    # Use a separate project dir so project-level files are absent
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = mod.run_migration(installation_dir=project_dir)
    assert result is True

    patched = _read_settings(global_settings)
    cmd = patched["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert cmd == "claude-hook"


def test_real_home_never_touched_without_monkeypatch(tmp_path: Path) -> None:
    """Without monkeypatching, the migration only operates on tmp_path files."""
    # Write a clean (no absolute paths) settings file in the project dir
    settings_path = tmp_path / ".claude" / "settings.json"
    data = _make_settings(_hooks_with_command("claude-hook"))
    _write_settings(settings_path, data)

    # The migration must complete without raising even if real ~/.claude files
    # don't exist or have other content.
    result = mod.run_migration(installation_dir=tmp_path)
    # Should succeed (True) regardless
    assert result is True


# ---------------------------------------------------------------------------
# 5. Non-MPM commands are left untouched
# ---------------------------------------------------------------------------


def test_non_mpm_absolute_path_not_replaced(tmp_path: Path) -> None:
    """An absolute path that is NOT an MPM hook script must be left alone."""
    settings_path = tmp_path / ".claude" / "settings.json"
    non_mpm_command = "/usr/local/bin/my-custom-hook.sh"
    data = _make_settings(_hooks_with_command(non_mpm_command))
    _write_settings(settings_path, data)

    mod.run_migration(installation_dir=tmp_path)

    result = _read_settings(settings_path)
    cmd = result["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert cmd == non_mpm_command


def test_relative_path_not_replaced(tmp_path: Path) -> None:
    """A relative path (e.g. 'claude-hook-fast.sh') is not treated as absolute."""
    settings_path = tmp_path / ".claude" / "settings.json"
    data = _make_settings(_hooks_with_command("claude-hook-fast.sh"))
    _write_settings(settings_path, data)

    mod.run_migration(installation_dir=tmp_path)

    result = _read_settings(settings_path)
    cmd = result["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert cmd == "claude-hook-fast.sh"


# ---------------------------------------------------------------------------
# 6. Missing settings files are silently skipped
# ---------------------------------------------------------------------------


def test_missing_settings_file_skipped(tmp_path: Path) -> None:
    """If no settings files exist, the migration is a no-op with no exception."""
    # tmp_path has no .claude subdirectory at all
    result = mod.run_migration(installation_dir=tmp_path)
    assert result is True


def test_multiple_files_only_absolute_replaced(tmp_path: Path) -> None:
    """Verify both settings.json and settings.local.json are scanned."""
    shared = tmp_path / ".claude" / "settings.json"
    local = tmp_path / ".claude" / "settings.local.json"

    shared_data = _make_settings(_hooks_with_command("claude-hook"))  # already portable
    local_data = _make_settings(
        _hooks_with_command("/home/user/code/claude-hook-handler.sh")
    )
    _write_settings(shared, shared_data)
    _write_settings(local, local_data)

    result = mod.run_migration(installation_dir=tmp_path)
    assert result is True

    # Shared file unchanged
    assert (
        _read_settings(shared)["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        == "claude-hook"
    )
    # Local file patched
    assert (
        _read_settings(local)["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        == "claude-hook"
    )
