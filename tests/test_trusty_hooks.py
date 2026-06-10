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


# ---------------------------------------------------------------------------
# Issue #717: robust cross-matcher-group dedup and bare-hook merge tests
# ---------------------------------------------------------------------------


def _bare_claude_hook(event: str = "SessionStart", timeout: int = 15) -> dict:
    """A bare MPM hook written by HookInstaller (no _mpm_service tag)."""
    return {
        "type": "command",
        "command": "claude-hook",
        "timeout": timeout,
        "_mpm": True,
    }


def _settings_with_bare_hook(event: str, matcher: str | None = "*") -> dict:
    """Settings file that HookInstaller wrote: bare claude-hook, no _mpm_service."""
    block: dict = {"hooks": [_bare_claude_hook(event)]}
    if matcher is not None:
        block["matcher"] = matcher
    return {"hooks": {event: [block]}}


def test_no_dup_when_bare_claude_hook_already_present_memory(
    user_home: Path,
) -> None:
    """inject_hooks_to_settings does not duplicate trusty-memory hooks when a bare
    claude-hook entry (written by HookInstaller, no _mpm_service) already exists for
    the same event.  The existing entry should get the _mpm_service tag merged onto
    it in-place; no second hook entry should be appended.
    """
    settings_path = user_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Pre-populate with a bare claude-hook for SessionStart (HookInstaller style).
    settings_path.write_text(
        json.dumps(_settings_with_bare_hook("SessionStart", matcher="*"), indent=2),
        encoding="utf-8",
    )

    changed = th.inject_hooks_to_settings(settings_path, ["trusty-memory"])

    assert changed is True, "Merging a tag counts as a change"
    data = _read(settings_path)

    # After the merge there must be exactly ONE hook in SessionStart.
    session_groups = data["hooks"]["SessionStart"]
    all_session_hooks: list[dict] = []
    for g in session_groups:
        all_session_hooks.extend(g.get("hooks", []))

    assert len(all_session_hooks) == 1, (
        f"Expected 1 hook in SessionStart after merge, got {len(all_session_hooks)}"
    )
    # The merged entry must carry the _mpm_service tag.
    assert all_session_hooks[0].get("_mpm_service") == "trusty-memory"


def test_no_dup_when_bare_claude_hook_already_present_search(
    user_home: Path,
) -> None:
    """inject_hooks_to_settings does not duplicate trusty-search hooks when a bare
    python3-module hook (written by HookInstaller) already exists for PostToolUse.
    """
    settings_path = user_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Pre-populate with a bare trusty_index_hook entry (no _mpm_service, but _mpm:true).
    bare_search_hook = {
        "type": "command",
        "command": "python3",
        "args": ["-m", "claude_mpm.hooks.trusty_index_hook"],
        "timeout": 10,
        "async": True,
        "_mpm": True,
        # Intentionally missing _mpm_service to simulate HookInstaller bare write.
    }
    initial = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Write|MultiEdit|Edit|NotebookEdit",
                    "hooks": [bare_search_hook],
                }
            ]
        }
    }
    settings_path.write_text(json.dumps(initial, indent=2), encoding="utf-8")

    changed = th.inject_hooks_to_settings(settings_path, ["trusty-search"])

    assert changed is True, "Merging the _mpm_service tag counts as a change"
    data = _read(settings_path)

    ptu_groups = data["hooks"]["PostToolUse"]
    all_ptu_hooks: list[dict] = []
    for g in ptu_groups:
        all_ptu_hooks.extend(g.get("hooks", []))

    assert len(all_ptu_hooks) == 1, (
        f"Expected 1 hook in PostToolUse after merge, got {len(all_ptu_hooks)}"
    )
    assert all_ptu_hooks[0].get("_mpm_service") == "trusty-search"


def test_second_inject_after_bare_hook_install_is_noop(user_home: Path) -> None:
    """Running inject_hooks_to_settings twice — first time when a bare claude-hook
    already exists (HookInstaller path), second time after merge — must be a no-op
    on the second run.
    """
    settings_path = user_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(_settings_with_bare_hook("SessionStart", matcher="*"), indent=2),
        encoding="utf-8",
    )

    # First injection: bare hook found, tag merged, changed=True.
    first = th.inject_hooks_to_settings(settings_path, ["trusty-memory"])
    assert first is True

    snapshot = settings_path.read_text(encoding="utf-8")

    # Second injection: hook is now tagged, dedup fires, changed=False.
    second = th.inject_hooks_to_settings(settings_path, ["trusty-memory"])
    assert second is False, "Second run must be a no-op after merge"
    assert settings_path.read_text(encoding="utf-8") == snapshot


def test_cross_matcher_group_dedup_memory(user_home: Path) -> None:
    """A trusty-memory hook in a DIFFERENT matcher group for the same event is
    detected as a duplicate and NOT re-added.  This covers the cross-matcher-group
    scenario where the existing hook lives under a different matcher string.
    """
    settings_path = user_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Place a trusty-memory hook under a non-standard matcher "startup" for SessionStart.
    existing_hook = {
        "type": "command",
        "command": "claude-hook",
        "timeout": 15,
        "_mpm": True,
        "_mpm_service": "trusty-memory",
    }
    initial = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup",  # Different matcher than the spec's "*"
                    "hooks": [existing_hook],
                }
            ]
        }
    }
    settings_path.write_text(json.dumps(initial, indent=2), encoding="utf-8")

    changed = th.inject_hooks_to_settings(settings_path, ["trusty-memory"])

    # The injection must not add a second hook under matcher "*".
    data = _read(settings_path)
    all_session_hooks: list[dict] = []
    for g in data["hooks"]["SessionStart"]:
        all_session_hooks.extend(g.get("hooks", []))

    assert len(all_session_hooks) == 1, (
        f"Cross-matcher-group dedup failed: expected 1 hook, got {len(all_session_hooks)}"
    )
    # The existing "startup" matcher group must still be there unchanged.
    assert data["hooks"]["SessionStart"][0]["matcher"] == "startup"


def test_inject_twice_produces_no_duplicates_for_both_services(
    user_home: Path,
) -> None:
    """inject_hooks_to_settings called twice for both trusty-memory and trusty-search
    must not produce duplicate entries — covers the always-on startup trigger scenario.
    """
    settings_path = user_home / ".claude" / "settings.json"

    # First invocation (simulates first startup).
    th.inject_hooks_to_settings(settings_path, ["trusty-memory", "trusty-search"])
    after_first = _read(settings_path)

    # Second invocation (simulates next startup/resume).
    second_changed = th.inject_hooks_to_settings(
        settings_path, ["trusty-memory", "trusty-search"]
    )
    after_second = _read(settings_path)

    assert second_changed is False, "Second run must be a no-op"
    assert after_first == after_second, "File must be byte-identical after two runs"

    # Verify no event has more than one hook per service.
    for event, groups in after_second["hooks"].items():
        all_hooks = []
        for g in groups:
            all_hooks.extend(g.get("hooks", []))
        services = [h.get("_mpm_service") for h in all_hooks if h.get("_mpm")]
        # No service should appear more than once per event.
        for svc in ("trusty-memory", "trusty-search"):
            count = services.count(svc)
            assert count <= 1, (
                f"Event {event!r}: found {count} hooks for {svc!r}, expected at most 1"
            )


# ---------------------------------------------------------------------------
# Issue #717: dedup migration recurring idempotency tests
# ---------------------------------------------------------------------------


class TestDedupMigrationRecurring:
    """Verify the dedup migration is safe to run repeatedly (run_always=True)."""

    def _run_migration_in(self, path: Path) -> bool:
        from unittest.mock import patch

        import claude_mpm.migrations.migrate_dedup_hook_registrations as dedup_mod

        with patch.object(Path, "cwd", return_value=path):
            return dedup_mod.run_migration()

    def test_migration_run_always_registered(self) -> None:
        """dedup_hook_registrations must be registered with run_always=True in the registry."""
        from claude_mpm.migrations.registry import MIGRATIONS

        matches = [m for m in MIGRATIONS if m.id == "dedup_hook_registrations"]
        assert matches, "dedup_hook_registrations migration not found in registry"
        assert matches[0].run_always is True, (
            "dedup_hook_registrations must have run_always=True so it fires on every startup"
        )

    def test_dedup_migration_repeated_run_is_noop(self, tmp_path: Path) -> None:
        """Running dedup migration twice on clean settings (no dupes) is a no-op."""
        # Write clean settings with a single hook per event (no duplicates).
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "matcher": "*",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "claude-hook",
                                        "timeout": 15,
                                        "_mpm": True,
                                        "_mpm_service": "trusty-memory",
                                    }
                                ],
                            }
                        ]
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        snapshot_before = settings_path.read_text(encoding="utf-8")

        # Run 1 — no duplicates to remove; file should not change.
        result1 = self._run_migration_in(tmp_path)
        assert result1 is True
        after_run1 = settings_path.read_text(encoding="utf-8")

        # Run 2 — same as run 1.
        result2 = self._run_migration_in(tmp_path)
        assert result2 is True
        after_run2 = settings_path.read_text(encoding="utf-8")

        # File should be unchanged from the initial clean state after both runs.
        # Note: the migration does NOT rewrite a file with no duplicates, so the
        # file content (including whitespace) should remain identical.
        assert after_run1 == snapshot_before, (
            "First migration run must not modify a file with no duplicate hooks"
        )
        assert after_run2 == after_run1, (
            "Second migration run must be a no-op when the file has no duplicate hooks"
        )

    def test_dedup_migration_collapses_then_stable(self, tmp_path: Path) -> None:
        """Migration collapses duplicates on first run, then is a no-op on second run."""
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Write settings with duplicates (the bug state).
        settings_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "matcher": "*",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "claude-hook",
                                        "timeout": 15,
                                        "_mpm": True,
                                    },
                                    {
                                        "type": "command",
                                        "command": "claude-hook",
                                        "timeout": 60,
                                        "_mpm": True,
                                    },
                                ],
                            }
                        ]
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        # First run: deduplicates.
        result1 = self._run_migration_in(tmp_path)
        assert result1 is True
        after_first = json.loads(settings_path.read_text(encoding="utf-8"))
        hooks_after_first = after_first["hooks"]["SessionStart"][0]["hooks"]
        assert len(hooks_after_first) == 1, "First run must collapse duplicates to 1"

        snapshot_after_first = settings_path.read_text(encoding="utf-8")

        # Second run: no-op.
        result2 = self._run_migration_in(tmp_path)
        assert result2 is True
        after_second = settings_path.read_text(encoding="utf-8")
        assert after_second == snapshot_after_first, (
            "Second migration run must not modify the already-deduped file"
        )
