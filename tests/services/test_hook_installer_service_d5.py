"""Tests for D5: HookInstallerService duplicate registration & broken validator.

D5(a): is_hooks_configured() validated by checking for hook_wrapper.sh /
       claude-hook-handler.sh substrings only.  The live config uses
       "claude-hook" (PATH entry point) with "_mpm": true marker, so the
       validator always returned False → spurious re-install every startup.

D5(b): install_hooks() can register "claude-hook" twice because is_our_hook()
       didn't recognise either the "_mpm": true marker or the literal
       "claude-hook" command.  Second install spawns a no-op extra process on
       every tool call.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from claude_mpm.services.hook_installer_service import HookInstallerService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(tmp_path: Path) -> HookInstallerService:
    """Create a HookInstallerService rooted at tmp_path."""
    svc = HookInstallerService.__new__(HookInstallerService)
    from claude_mpm.core.logging_config import get_logger

    svc.logger = get_logger(__name__)
    svc.project_root = tmp_path
    svc.claude_dir = tmp_path / ".claude"
    svc.claude_dir.mkdir(parents=True, exist_ok=True)
    svc.settings_file = svc.claude_dir / "settings.json"
    return svc


def _write_settings(path: Path, hooks_payload: dict[str, Any]) -> None:
    settings = {"hooks": hooks_payload}
    path.write_text(json.dumps(settings, indent=2))


def _mpm_hook_entry(command: str = "claude-hook", timeout: int = 60) -> dict[str, Any]:
    """Build a hook entry that matches what install_hooks() writes."""
    return {"type": "command", "command": command, "timeout": timeout, "_mpm": True}


def _settings_with_mpm_hooks(
    event_types: list[str], command: str = "claude-hook"
) -> dict[str, Any]:
    """Build a complete hooks payload with one _mpm entry per event type."""
    hooks: dict[str, Any] = {}
    for event_type in event_types:
        hooks[event_type] = [
            {"matcher": "*", "hooks": [_mpm_hook_entry(command=command)]}
        ]
    return hooks


REQUIRED_EVENTS = [
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SubagentStop",
]


# ===========================================================================
# D5(a): is_hooks_configured() validator tests
# ===========================================================================


class TestIsHooksConfiguredD5a:
    """is_hooks_configured() must accept _mpm:true / claude-hook as configured."""

    def test_mpm_marker_is_recognised_as_configured(self, tmp_path):
        """Config with _mpm:true on all required events → True."""
        svc = _make_service(tmp_path)
        _write_settings(svc.settings_file, _settings_with_mpm_hooks(REQUIRED_EVENTS))
        assert svc.is_hooks_configured() is True

    def test_claude_hook_command_without_marker_is_recognised(self, tmp_path):
        """Config with command == "claude-hook" (no _mpm key) → True.

        The entry point alone should be sufficient to recognise the config.
        """
        svc = _make_service(tmp_path)
        # No _mpm marker — only the command name
        hooks: dict[str, Any] = {}
        for event_type in REQUIRED_EVENTS:
            hooks[event_type] = [
                {
                    "matcher": "*",
                    "hooks": [
                        {"type": "command", "command": "claude-hook", "timeout": 60}
                    ],
                }
            ]
        _write_settings(svc.settings_file, hooks)
        assert svc.is_hooks_configured() is True

    def test_legacy_hook_wrapper_sh_still_recognised(self, tmp_path):
        """Legacy hook_wrapper.sh configs (old installs) still return True."""
        svc = _make_service(tmp_path)
        hooks: dict[str, Any] = {}
        for event_type in REQUIRED_EVENTS:
            hooks[event_type] = [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/path/to/hook_wrapper.sh",
                            "timeout": 60,
                        }
                    ],
                }
            ]
        _write_settings(svc.settings_file, hooks)
        assert svc.is_hooks_configured() is True

    def test_legacy_claude_hook_handler_sh_still_recognised(self, tmp_path):
        """Legacy claude-hook-handler.sh configs still return True."""
        svc = _make_service(tmp_path)
        hooks: dict[str, Any] = {}
        for event_type in REQUIRED_EVENTS:
            hooks[event_type] = [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/some/path/claude-hook-handler.sh",
                            "timeout": 60,
                        }
                    ],
                }
            ]
        _write_settings(svc.settings_file, hooks)
        assert svc.is_hooks_configured() is True

    def test_missing_settings_file_returns_false(self, tmp_path):
        svc = _make_service(tmp_path)
        # Settings file does not exist
        assert svc.is_hooks_configured() is False

    def test_no_hooks_section_returns_false(self, tmp_path):
        svc = _make_service(tmp_path)
        svc.settings_file.write_text(json.dumps({"model": "sonnet"}))
        assert svc.is_hooks_configured() is False

    def test_missing_required_event_returns_false(self, tmp_path):
        """If even one required event is missing the whole check fails."""
        svc = _make_service(tmp_path)
        incomplete = [e for e in REQUIRED_EVENTS if e != "SubagentStop"]
        _write_settings(svc.settings_file, _settings_with_mpm_hooks(incomplete))
        assert svc.is_hooks_configured() is False

    def test_unknown_command_returns_false(self, tmp_path):
        """A hook with an unrecognised command and no _mpm marker → False."""
        svc = _make_service(tmp_path)
        hooks: dict[str, Any] = {}
        for event_type in REQUIRED_EVENTS:
            hooks[event_type] = [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/some/other-hook.sh",
                            "timeout": 60,
                        }
                    ],
                }
            ]
        _write_settings(svc.settings_file, hooks)
        assert svc.is_hooks_configured() is False


# ===========================================================================
# D5(b): install_hooks() idempotency tests
# ===========================================================================


class TestInstallHooksIdempotentD5b:
    """Running install_hooks() twice must not produce duplicate hook entries."""

    def _run_install(self, svc: HookInstallerService) -> None:
        """Call install_hooks() with mocked shutil.which returning claude-hook."""
        with patch(
            "claude_mpm.services.hook_installer_service.shutil.which",
            return_value="/usr/local/bin/claude-hook",
        ):
            result = svc.install_hooks()
        assert result is True, "install_hooks() returned False"

    def _count_mpm_hooks_for_event(
        self, settings: dict[str, Any], event_type: str
    ) -> int:
        """Count hook entries that belong to claude-mpm for a given event."""
        count = 0
        for block in settings.get("hooks", {}).get(event_type, []):
            for hook in block.get("hooks", []):
                if (
                    hook.get("_mpm")
                    or hook.get("command") == "claude-hook"
                    or "hook_wrapper.sh" in hook.get("command", "")
                    or "claude-hook-handler.sh" in hook.get("command", "")
                ):
                    count += 1
        return count

    def test_first_install_adds_exactly_one_entry_per_event(self, tmp_path):
        """Fresh install produces exactly one MPM hook entry per required event."""
        svc = _make_service(tmp_path)
        self._run_install(svc)

        with svc.settings_file.open() as f:
            settings = json.load(f)

        for event_type in REQUIRED_EVENTS:
            count = self._count_mpm_hooks_for_event(settings, event_type)
            assert count == 1, f"Expected 1 MPM hook for {event_type}, found {count}"

    def test_second_install_does_not_add_duplicates(self, tmp_path):
        """Running install_hooks() twice must not double the hook entries."""
        svc = _make_service(tmp_path)

        # First install
        self._run_install(svc)

        # Second install on the same settings file
        self._run_install(svc)

        with svc.settings_file.open() as f:
            settings = json.load(f)

        for event_type in REQUIRED_EVENTS:
            count = self._count_mpm_hooks_for_event(settings, event_type)
            assert count == 1, (
                f"Duplicate detected: {count} MPM hooks for {event_type} "
                "after two installs"
            )

    def test_install_on_config_with_mpm_marker_is_idempotent(self, tmp_path):
        """install_hooks() on a config that already has _mpm:true does not add more."""
        svc = _make_service(tmp_path)
        # Pre-write a valid MPM config
        _write_settings(svc.settings_file, _settings_with_mpm_hooks(REQUIRED_EVENTS))

        # is_hooks_configured() now returns True → install_hooks() is a no-op
        with patch(
            "claude_mpm.services.hook_installer_service.shutil.which",
            return_value="/usr/local/bin/claude-hook",
        ):
            result = svc.install_hooks(force=False)

        assert result is True

        with svc.settings_file.open() as f:
            settings = json.load(f)

        for event_type in REQUIRED_EVENTS:
            count = self._count_mpm_hooks_for_event(settings, event_type)
            assert count == 1, (
                f"Expected 1 MPM hook for {event_type} after no-op install, "
                f"found {count}"
            )
