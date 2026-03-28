"""Tests for stale hook entry cleanup from ~/.claude/settings.json.

Covers:
- Stale entries are removed (path contains claude-mpm/claude-hook and file
  doesn't exist on disk)
- Valid entries from other tools are preserved
- No-op when no stale entries exist (file not modified)
- Handles missing ~/.claude/settings.json gracefully
- Handles settings.json with no hooks key gracefully
- cleanup_user_level_hooks() integrates both directory and settings cleanup
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hook_entry(command: str, with_matcher: bool = False) -> dict:
    """Build a minimal hook entry dict as written by HookInstaller."""
    cmd_obj = {"type": "command", "command": command}
    entry: dict = {"hooks": [cmd_obj]}
    if with_matcher:
        entry["matcher"] = "*"
    return entry


# ---------------------------------------------------------------------------
# _is_stale_hook_command unit tests
# ---------------------------------------------------------------------------


class TestIsStaleHookCommand:
    """Unit tests for the _is_stale_hook_command predicate."""

    def _call(self, command: str) -> bool:
        from claude_mpm.cli.startup import _is_stale_hook_command

        return _is_stale_hook_command(command)

    def test_empty_command_is_not_stale(self):
        assert self._call("") is False

    def test_unrelated_command_is_not_stale(self):
        assert self._call("/usr/local/bin/some-other-tool") is False

    def test_entry_point_claude_hook_is_not_stale(self):
        """'claude-hook' (no path) is resolved via PATH at runtime — not stale."""
        assert self._call("claude-hook") is False

    def test_relative_path_with_claude_hook_is_not_stale(self):
        """Relative paths are not absolute-path validated."""
        assert self._call("bin/claude-hook") is False

    def test_absolute_path_containing_claude_mpm_nonexistent_is_stale(self, tmp_path):
        stale_path = str(tmp_path / "claude-mpm" / "scripts" / "hook.sh")
        # File does NOT exist at stale_path
        assert self._call(stale_path) is True

    def test_absolute_path_containing_claude_hook_nonexistent_is_stale(self, tmp_path):
        stale_path = str(tmp_path / "bin" / "claude-hook-fast.sh")
        assert self._call(stale_path) is True

    def test_absolute_path_claude_mpm_existing_is_not_stale(self, tmp_path):
        """An absolute path that actually exists is not stale."""
        existing = tmp_path / "claude-mpm" / "scripts" / "hook.sh"
        existing.parent.mkdir(parents=True)
        existing.touch()
        assert self._call(str(existing)) is False

    def test_absolute_path_claude_hook_existing_is_not_stale(self, tmp_path):
        existing = tmp_path / "claude-hook-fast.sh"
        existing.touch()
        assert self._call(str(existing)) is False


# ---------------------------------------------------------------------------
# _cleanup_stale_settings_json_hooks unit tests
# ---------------------------------------------------------------------------


class TestCleanupStaleSettingsJsonHooks:
    """Unit tests for _cleanup_stale_settings_json_hooks."""

    def _call(self) -> int:
        from claude_mpm.cli.startup import _cleanup_stale_settings_json_hooks

        return _cleanup_stale_settings_json_hooks()

    def test_missing_settings_file_returns_zero(self, tmp_path):
        """When ~/.claude/settings.json does not exist, return 0."""
        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 0

    def test_settings_without_hooks_key_returns_zero(self, tmp_path):
        """When settings.json has no 'hooks' key, return 0."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        settings = claude_dir / "settings.json"
        settings.write_text(json.dumps({"permissions": {"allow": []}}))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 0

    def test_no_stale_entries_returns_zero_and_file_unchanged(self, tmp_path):
        """When all hook entries reference existing files, nothing is removed."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        # Create a real script file so the path "exists"
        script = tmp_path / "claude-hook-fast.sh"
        script.touch()

        original_data = {
            "hooks": {
                "SessionStart": [
                    _make_hook_entry(str(script), with_matcher=True)
                ]
            }
        }
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps(original_data, indent=2))
        original_mtime = settings_file.stat().st_mtime

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 0
        # File must not have been rewritten
        assert settings_file.stat().st_mtime == original_mtime

    def test_stale_entry_is_removed(self, tmp_path):
        """A hook entry pointing to a non-existent claude-mpm script is removed."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        stale_path = str(tmp_path / "pipx" / "venvs" / "claude-mpm" / "scripts" / "claude-hook-fast.sh")
        # stale_path does NOT exist on disk

        data = {
            "hooks": {
                "SessionStart": [
                    _make_hook_entry(stale_path, with_matcher=True)
                ]
            }
        }
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps(data))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 1  # one command removed
        cleaned = json.loads(settings_file.read_text())
        # Event key should be gone since entry is empty
        assert "SessionStart" not in cleaned.get("hooks", {})

    def test_entries_from_other_tools_are_preserved(self, tmp_path):
        """Hook entries not belonging to claude-mpm are never removed."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        stale_path = str(tmp_path / "claude-mpm" / "nonexistent.sh")

        other_tool_entry = _make_hook_entry("/usr/local/bin/some-other-hook")
        stale_entry = _make_hook_entry(stale_path)

        data = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"type": "command", "command": "/usr/local/bin/some-other-hook"},
                            {"type": "command", "command": stale_path},
                        ],
                    }
                ]
            }
        }
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps(data))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 1  # only the stale command removed
        cleaned = json.loads(settings_file.read_text())
        session_hooks = cleaned["hooks"]["SessionStart"]
        assert len(session_hooks) == 1
        remaining_cmds = session_hooks[0]["hooks"]
        assert len(remaining_cmds) == 1
        assert remaining_cmds[0]["command"] == "/usr/local/bin/some-other-hook"

    def test_multiple_stale_entries_across_events_all_removed(self, tmp_path):
        """Multiple stale entries across different event types are all removed."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        stale1 = str(tmp_path / "claude-mpm" / "scripts" / "hook.sh")
        stale2 = str(tmp_path / "claude-hook-handler.sh")

        data = {
            "hooks": {
                "SessionStart": [_make_hook_entry(stale1, with_matcher=True)],
                "Stop": [_make_hook_entry(stale2)],
            }
        }
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps(data))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 2
        cleaned = json.loads(settings_file.read_text())
        assert cleaned.get("hooks", {}) == {}

    def test_non_hooks_settings_are_preserved(self, tmp_path):
        """Non-hook settings keys (permissions, mcpServers, etc.) survive cleanup."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        stale_path = str(tmp_path / "claude-mpm" / "hook.sh")

        data = {
            "permissions": {"allow": ["Bash"]},
            "enableAllProjectMcpServers": True,
            "outputStyle": "claude_mpm",
            "hooks": {
                "Stop": [_make_hook_entry(stale_path)]
            },
        }
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps(data))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 1
        cleaned = json.loads(settings_file.read_text())
        assert cleaned["permissions"] == {"allow": ["Bash"]}
        assert cleaned["enableAllProjectMcpServers"] is True
        assert cleaned["outputStyle"] == "claude_mpm"

    def test_entry_point_command_not_removed(self, tmp_path):
        """The 'claude-hook' entry-point command is PATH-resolved — never removed."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        data = {
            "hooks": {
                "Stop": [_make_hook_entry("claude-hook")]
            }
        }
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps(data))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 0

    def test_invalid_json_returns_zero(self, tmp_path):
        """Corrupted settings.json is handled gracefully."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        settings_file = claude_dir / "settings.json"
        settings_file.write_text("{not valid json")

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 0

    def test_empty_hooks_section_after_cleanup(self, tmp_path):
        """When all hook entries are removed, the hooks key becomes empty dict."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        stale = str(tmp_path / "claude-mpm" / "scripts" / "fast-hook.sh")

        data = {
            "hooks": {
                "SessionStart": [_make_hook_entry(stale, with_matcher=True)],
                "PreToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"type": "command", "command": stale},
                        ],
                    }
                ],
            }
        }
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps(data))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 2
        cleaned = json.loads(settings_file.read_text())
        # Hooks dict should be empty (all events removed)
        assert cleaned["hooks"] == {}

    def test_mixed_valid_and_stale_same_entry(self, tmp_path):
        """When one entry has both a valid and stale command, only stale is removed."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        # Valid script (actually exists)
        valid_script = tmp_path / "claude-hook-fast.sh"
        valid_script.touch()

        stale_path = str(tmp_path / "pipx" / "claude-mpm" / "hook.sh")

        data = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"type": "command", "command": str(valid_script)},
                            {"type": "command", "command": stale_path},
                        ],
                    }
                ]
            }
        }
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps(data))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result == 1
        cleaned = json.loads(settings_file.read_text())
        session_hooks = cleaned["hooks"]["SessionStart"]
        assert len(session_hooks) == 1
        remaining = session_hooks[0]["hooks"]
        assert len(remaining) == 1
        assert remaining[0]["command"] == str(valid_script)


# ---------------------------------------------------------------------------
# cleanup_user_level_hooks integration tests
# ---------------------------------------------------------------------------


class TestCleanupUserLevelHooksIntegration:
    """Integration tests for cleanup_user_level_hooks() combining both steps."""

    def _call(self) -> bool:
        from claude_mpm.cli.startup import cleanup_user_level_hooks

        return cleanup_user_level_hooks()

    def test_nothing_to_clean_returns_false(self, tmp_path):
        """When neither the directory nor stale entries exist, return False."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"permissions": {"allow": []}}))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result is False

    def test_directory_cleanup_returns_true(self, tmp_path):
        """When the stale hooks directory exists, cleanup returns True."""
        hooks_dir = tmp_path / ".claude" / "hooks" / "claude-mpm"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "hook.sh").touch()

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result is True
        assert not hooks_dir.exists()

    def test_stale_settings_cleanup_returns_true(self, tmp_path):
        """When stale settings.json entries exist, cleanup returns True."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        stale_path = str(tmp_path / "claude-mpm" / "hook.sh")
        data = {
            "hooks": {
                "SessionStart": [_make_hook_entry(stale_path, with_matcher=True)]
            }
        }
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps(data))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result is True
        cleaned = json.loads(settings_file.read_text())
        assert cleaned.get("hooks", {}) == {}

    def test_both_cleanups_run(self, tmp_path):
        """Both directory and settings cleanup run in the same call."""
        # Stale directory
        hooks_dir = tmp_path / ".claude" / "hooks" / "claude-mpm"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "hook.sh").touch()

        # Stale settings entry
        stale_path = str(tmp_path / "claude-mpm" / "hook.sh")
        data = {
            "hooks": {
                "Stop": [_make_hook_entry(stale_path)]
            }
        }
        settings_file = tmp_path / ".claude" / "settings.json"
        settings_file.write_text(json.dumps(data))

        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result is True
        assert not hooks_dir.exists()
        cleaned = json.loads(settings_file.read_text())
        assert cleaned.get("hooks", {}) == {}

    def test_no_settings_file_is_graceful(self, tmp_path):
        """Missing ~/.claude/settings.json does not raise an exception."""
        # No .claude directory at all
        with patch.object(Path, "home", return_value=tmp_path):
            result = self._call()

        assert result is False
