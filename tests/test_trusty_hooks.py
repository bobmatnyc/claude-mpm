"""Tests for the shared trusty hook-injection module.

These cover the console-free :mod:`claude_mpm.services.trusty_hooks` helpers
used by both the interactive setup command and the startup autodetect
migration: idempotent injection, legacy-hook stripping, the "project settings
only if it already exists" rule, and structural parity with the hook layout the
old ``TrustyMixin`` path produced.
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - used at runtime in fixtures

import pytest

from claude_mpm.services import trusty_hooks as th


@pytest.fixture
def user_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``Path.home()`` to a temp dir so ~/.claude is sandboxed."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))
    return home


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _all_hooks(settings: dict) -> list[dict]:
    """Flatten every hook dict across all events/groups."""
    out: list[dict] = []
    for groups in settings.get("hooks", {}).values():
        for group in groups:
            out.extend(group.get("hooks", []))
    return out


def test_injects_memory_hooks_into_new_user_settings(user_home: Path) -> None:
    """Memory hooks land in a freshly-created ~/.claude/settings.json."""
    settings_path = user_home / ".claude" / "settings.json"
    assert not settings_path.exists()

    changed = th.inject_hooks_to_settings(settings_path, ["trusty-memory"])

    assert changed is True
    data = _read(settings_path)
    services = {h.get("_mpm_service") for h in _all_hooks(data)}
    assert services == {"trusty-memory"}
    # SessionStart, Stop, SubagentStop → three groups under matcher "*".
    assert set(data["hooks"]) == {"SessionStart", "Stop", "SubagentStop"}


def test_idempotent_second_run_is_noop(user_home: Path) -> None:
    """Re-running injection does not duplicate hooks and reports no change."""
    settings_path = user_home / ".claude" / "settings.json"

    first = th.inject_hooks_to_settings(settings_path, ["trusty-memory"])
    snapshot = settings_path.read_text(encoding="utf-8")
    second = th.inject_hooks_to_settings(settings_path, ["trusty-memory"])

    assert first is True
    assert second is False, "Second run must be a no-op (dedup by _mpm_service)"
    assert settings_path.read_text(encoding="utf-8") == snapshot


def test_strips_legacy_hooks(user_home: Path) -> None:
    """kuzu-memory / mcp-vector-search hooks are removed on injection."""
    settings_path = user_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {"type": "command", "_mpm_service": "kuzu-memory"},
                                {"type": "command", "command": "user-script.sh"},
                            ],
                        }
                    ],
                    "PostToolUse": [
                        {
                            "matcher": "Write",
                            "hooks": [
                                {"_mpm_service": "mcp-vector-search"},
                            ],
                        }
                    ],
                }
            },
            indent=2,
        )
    )

    changed = th.inject_hooks_to_settings(settings_path, ["trusty-memory"])

    assert changed is True
    data = _read(settings_path)
    services = {h.get("_mpm_service") for h in _all_hooks(data)}
    assert "kuzu-memory" not in services
    assert "mcp-vector-search" not in services
    assert "trusty-memory" in services
    # Unrelated user hook survives.
    commands = {h.get("command") for h in _all_hooks(data)}
    assert "user-script.sh" in commands


def test_inject_trusty_hooks_skips_absent_project_settings(
    user_home: Path, tmp_path: Path
) -> None:
    """Project settings are NOT created when ./.claude/settings.json is absent."""
    project = tmp_path / "proj"
    project.mkdir()
    project_settings = project / ".claude" / "settings.json"
    user_settings = user_home / ".claude" / "settings.json"

    changed = th.inject_trusty_hooks(["trusty-memory"], project_dir=project)

    assert changed is True
    assert not project_settings.exists(), "Must not create project settings silently"
    assert user_settings.exists(), "User settings must be created/updated"


def test_inject_trusty_hooks_updates_existing_project_settings(
    user_home: Path, tmp_path: Path
) -> None:
    """Project settings ARE updated when the file already exists."""
    project = tmp_path / "proj"
    project_settings = project / ".claude" / "settings.json"
    project_settings.parent.mkdir(parents=True)
    project_settings.write_text(json.dumps({"hooks": {}}, indent=2))

    changed = th.inject_trusty_hooks(["trusty-search"], project_dir=project)

    assert changed is True
    data = _read(project_settings)
    services = {h.get("_mpm_service") for h in _all_hooks(data)}
    assert services == {"trusty-search"}


def test_parity_with_legacy_specs_structure(user_home: Path) -> None:
    """Lock the produced structure to the historical TrustyMixin layout.

    The old ``TrustyMixin._inject_hooks_to_settings`` produced, for
    trusty-memory + trusty-search, hooks tagged ``_mpm: True`` /
    ``_mpm_service: <name>`` grouped by (event, matcher) with the exact specs
    in ``_TRUSTY_HOOK_SPECS``. This test pins that contract.
    """
    settings_path = user_home / ".claude" / "settings.json"
    th.inject_hooks_to_settings(settings_path, ["trusty-memory", "trusty-search"])
    data = _read(settings_path)

    # Memory: three events under matcher "*", each one claude-hook command.
    for event in ("SessionStart", "Stop", "SubagentStop"):
        groups = data["hooks"][event]
        assert len(groups) == 1
        assert groups[0]["matcher"] == "*"
        hook = groups[0]["hooks"][0]
        assert hook == {
            "type": "command",
            "command": "claude-hook",
            "timeout": 15,
            "_mpm": True,
            "_mpm_service": "trusty-memory",
        }

    # Search: PostToolUse under the edit matcher, async python module hook.
    ptu = data["hooks"]["PostToolUse"]
    assert len(ptu) == 1
    assert ptu[0]["matcher"] == "Write|MultiEdit|Edit|NotebookEdit"
    assert ptu[0]["hooks"][0] == {
        "type": "command",
        "command": "python3",
        "args": ["-m", "claude_mpm.hooks.trusty_index_hook"],
        "timeout": 10,
        "async": True,
        "_mpm": True,
        "_mpm_service": "trusty-search",
    }


def test_malformed_settings_is_skipped_not_corrupted(user_home: Path) -> None:
    """A non-JSON settings file is left untouched (skip, never corrupt)."""
    settings_path = user_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{ this is not json")

    changed = th.inject_hooks_to_settings(settings_path, ["trusty-memory"])

    assert changed is False
    # File preserved verbatim — not overwritten with a skeleton.
    assert settings_path.read_text(encoding="utf-8") == "{ this is not json"
