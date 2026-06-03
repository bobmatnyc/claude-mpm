"""Tests for the v6_3_1_deploy_claude_assets migration.

Coverage:
1. Deploys all expected assets into ~/.claude/ (monkeypatched home).
2. statusline.sh is made executable (chmod 0o755) on deploy.
3. Idempotency: running migration twice leaves files unchanged.
4. Pre-existing file without MPM marker is preserved (not overwritten).
5. Pre-existing MPM-managed statusline.sh is upgraded to current template.
6. settings.json is NOT overwritten when it already exists.
7. No absolute paths in deployed settings.json hook command fields (#611 regression guard).
8. No absolute paths in the bundled settings.json template.
9. force=True replaces a user-customised statusline.sh without MPM marker.
10. Registry: v6_3_1_deploy_claude_assets migration is discoverable.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

import claude_mpm.migrations.v6_3_1_deploy_claude_assets as mod
from claude_mpm.migrations.registry import MIGRATIONS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_home_and_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    force: bool = False,
) -> bool:
    """Patch Path.home() to tmp_path and run the migration.

    Why: The migration always targets ~/.claude/.  Redirecting home lets us
    test without touching the real developer environment.
    """
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    # Also patch the module-level constant that pre-calculates the user path.
    monkeypatch.setattr(
        mod,
        "_USER_SCRIPT_PATH",
        tmp_path / ".claude" / "hooks" / "scripts" / "statusline.sh",
    )
    return mod.run_migration(force=force)


def _deployed_statusline(fake_home: Path) -> Path:
    return fake_home / ".claude" / "hooks" / "scripts" / "statusline.sh"


def _deployed_settings(fake_home: Path) -> Path:
    return fake_home / ".claude" / "settings.json"


def _extract_all_hook_commands(settings: dict) -> list[str]:
    """Recursively collect every 'command' value inside a hooks subtree.

    Why: We need to assert that none of the deployed hook commands are
    absolute paths (regression guard for issue #611).
    """
    commands: list[str] = []
    hooks = settings.get("hooks", {})
    for event_entries in hooks.values():
        for entry in event_entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                if cmd:
                    commands.append(cmd)
    return commands


# ---------------------------------------------------------------------------
# 1. All expected assets are deployed
# ---------------------------------------------------------------------------


def test_statusline_deployed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """statusline.sh is created inside ~/.claude/hooks/scripts/ when absent.

    Why: Verifies the happy-path deployment of the primary script asset.
    Test: Run migration with monkeypatched home; assert the file exists and
    is non-empty.
    """
    result = _fake_home_and_run(tmp_path, monkeypatch)

    assert result is True
    target = _deployed_statusline(tmp_path)
    assert target.exists(), "statusline.sh should be deployed"
    assert target.stat().st_size > 0, "statusline.sh should not be empty"


def test_settings_deployed_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """settings.json is created in ~/.claude/ when absent.

    Why: Verifies the second deployment path.
    Test: Run migration; assert settings.json exists and is valid JSON.
    """
    _fake_home_and_run(tmp_path, monkeypatch)

    target = _deployed_settings(tmp_path)
    assert target.exists(), "settings.json should be deployed"
    data = json.loads(target.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "Deployed settings.json must be valid JSON object"


def test_parent_directories_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Intermediate directories (.claude/, hooks/scripts/) are created automatically.

    Why: Users who have never run Claude Code may not have these directories.
    Test: Start with empty tmp_path; verify both nested dirs exist after migration.
    """
    _fake_home_and_run(tmp_path, monkeypatch)

    assert (tmp_path / ".claude").is_dir()
    assert (tmp_path / ".claude" / "hooks" / "scripts").is_dir()


# ---------------------------------------------------------------------------
# 2. statusline.sh is executable after deployment
# ---------------------------------------------------------------------------


def test_statusline_is_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """statusline.sh must have execute bits (0o755) after deployment.

    Why: The script is invoked directly by Claude Code; a missing execute bit
    would silently break the status line.
    Test: Check st_mode after migration — user/group/other execute bits set.
    """
    _fake_home_and_run(tmp_path, monkeypatch)

    target = _deployed_statusline(tmp_path)
    mode = target.stat().st_mode
    assert mode & stat.S_IXUSR, "Owner execute bit must be set"
    assert mode & stat.S_IXGRP, "Group execute bit must be set"
    assert mode & stat.S_IXOTH, "Other execute bit must be set"


def test_executable_bit_set_on_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Execute bit is set even when statusline.sh already exists and is up-to-date.

    Why: A user may have copied the file without execute permission.
    Test: Pre-create the file with the MPM marker but no execute bit; verify
    chmod is applied.
    """
    scripts_dir = tmp_path / ".claude" / "hooks" / "scripts"
    scripts_dir.mkdir(parents=True)
    existing = scripts_dir / "statusline.sh"
    # Write content identical to the template so it's "already up to date"
    from importlib.resources import files

    content = (
        files("claude_mpm")
        / "templates"
        / "claude"
        / "hooks"
        / "scripts"
        / "statusline.sh"
    ).read_text(encoding="utf-8")
    existing.write_text(content, encoding="utf-8")
    # Remove all execute bits
    existing.chmod(0o644)

    _fake_home_and_run(tmp_path, monkeypatch)

    mode = existing.stat().st_mode
    assert mode & stat.S_IXUSR, "Execute bit should have been restored"


# ---------------------------------------------------------------------------
# 3. Idempotency
# ---------------------------------------------------------------------------


def test_second_run_is_noop_for_statusline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running the migration twice leaves statusline.sh content unchanged.

    Why: The migration must not clobber user modifications on repeated runs.
    Test: Run twice; compare file content and mtime of statusline.sh.
    """
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(
        mod,
        "_USER_SCRIPT_PATH",
        tmp_path / ".claude" / "hooks" / "scripts" / "statusline.sh",
    )

    mod.run_migration()
    first_content = _deployed_statusline(tmp_path).read_text(encoding="utf-8")
    first_mtime = _deployed_statusline(tmp_path).stat().st_mtime

    mod.run_migration()
    second_content = _deployed_statusline(tmp_path).read_text(encoding="utf-8")
    second_mtime = _deployed_statusline(tmp_path).stat().st_mtime

    assert first_content == second_content, "Content must not change on second run"
    assert first_mtime == second_mtime, (
        "mtime must not change on second run (no rewrite)"
    )


def test_second_run_is_noop_for_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running the migration twice leaves settings.json content unchanged.

    Why: settings.json is create-only; re-running must not modify existing file.
    Test: Run twice; compare content (mtime may differ due to OS resolution).
    """
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(
        mod,
        "_USER_SCRIPT_PATH",
        tmp_path / ".claude" / "hooks" / "scripts" / "statusline.sh",
    )

    mod.run_migration()
    first_content = _deployed_settings(tmp_path).read_text(encoding="utf-8")

    mod.run_migration()
    second_content = _deployed_settings(tmp_path).read_text(encoding="utf-8")

    assert first_content == second_content, (
        "settings.json must not be modified on second run"
    )


# ---------------------------------------------------------------------------
# 4. Pre-existing user-customised statusline.sh is preserved
# ---------------------------------------------------------------------------


def test_user_customised_statusline_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A statusline.sh without the MPM marker is not overwritten (force=False).

    Why: Respects user customisations; only MPM-managed copies are auto-upgraded.
    Test: Write a custom script without MPM_MARKER; run migration; verify content
    is unchanged.
    """
    scripts_dir = tmp_path / ".claude" / "hooks" / "scripts"
    scripts_dir.mkdir(parents=True)
    custom_content = "#!/bin/bash\necho 'my custom statusline'\n"
    existing = scripts_dir / "statusline.sh"
    existing.write_text(custom_content, encoding="utf-8")

    _fake_home_and_run(tmp_path, monkeypatch, force=False)

    assert existing.read_text(encoding="utf-8") == custom_content, (
        "User-customised statusline.sh must not be overwritten (force=False)"
    )


# ---------------------------------------------------------------------------
# 5. MPM-managed statusline.sh is upgraded when template changes
# ---------------------------------------------------------------------------


def test_mpm_managed_statusline_upgraded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An outdated MPM-managed statusline.sh (with MPM marker) is upgraded.

    Why: MPM owns files with the marker and should keep them current.
    Test: Write an old version (with MPM marker); run migration; verify content
    matches the bundled template.
    """
    scripts_dir = tmp_path / ".claude" / "hooks" / "scripts"
    scripts_dir.mkdir(parents=True)
    old_content = f"#!/bin/bash\n# {mod.MPM_MARKER}\necho 'old statusline'\n"
    existing = scripts_dir / "statusline.sh"
    existing.write_text(old_content, encoding="utf-8")

    _fake_home_and_run(tmp_path, monkeypatch)

    updated = existing.read_text(encoding="utf-8")
    assert updated != old_content, "Outdated MPM-managed file should be upgraded"
    assert mod.MPM_MARKER in updated, "Upgraded file should retain MPM marker"


# ---------------------------------------------------------------------------
# 6. settings.json is NOT overwritten when present
# ---------------------------------------------------------------------------


def test_settings_not_overwritten_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Existing settings.json is never overwritten.

    Why: The create-only policy protects existing user/team configurations.
    Test: Write a custom settings.json; run migration; assert original preserved.
    """
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    original_content = '{"my_custom_key": "my_custom_value"}\n'
    target = claude_dir / "settings.json"
    target.write_text(original_content, encoding="utf-8")

    _fake_home_and_run(tmp_path, monkeypatch)

    assert target.read_text(encoding="utf-8") == original_content, (
        "settings.json must not be overwritten when it already exists"
    )


# ---------------------------------------------------------------------------
# 7 & 8. No absolute paths in hook commands (regression guard for #611)
# ---------------------------------------------------------------------------


def test_deployed_settings_no_absolute_hook_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No hook command in the deployed settings.json should be an absolute path.

    Why: Absolute paths break portability and were the root cause of issue #611.
    Test: Deploy settings.json; extract all 'command' values from hooks subtree;
    assert none starts with '/'.
    """
    _fake_home_and_run(tmp_path, monkeypatch)

    target = _deployed_settings(tmp_path)
    data = json.loads(target.read_text(encoding="utf-8"))
    commands = _extract_all_hook_commands(data)

    absolute_commands = [c for c in commands if c.startswith("/")]
    assert not absolute_commands, (
        f"Deployed settings.json must not contain absolute hook commands. "
        f"Found: {absolute_commands}"
    )


def test_bundled_template_settings_no_absolute_hook_paths() -> None:
    """The bundled template settings.json contains no absolute hook command paths.

    Why: Guards against the template itself shipping absolute paths that would
    affect all new users on deployment (regression guard for #611).
    Test: Read template directly via importlib.resources; check all hook commands.
    """
    from importlib.resources import files

    raw = (files("claude_mpm") / "templates" / "claude" / "settings.json").read_text(
        encoding="utf-8"
    )
    data = json.loads(raw)
    commands = _extract_all_hook_commands(data)

    absolute_commands = [c for c in commands if c.startswith("/")]
    assert not absolute_commands, (
        f"Bundled settings.json template must not contain absolute hook commands. "
        f"Found: {absolute_commands}"
    )


# ---------------------------------------------------------------------------
# 9. force=True replaces a user-customised statusline.sh
# ---------------------------------------------------------------------------


def test_force_replaces_custom_statusline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With force=True, a user-customised statusline.sh (no MPM marker) is replaced.

    Why: Provides an escape hatch for explicit user-driven refresh operations.
    Test: Write custom file without MPM marker; run with force=True; assert
    content was replaced with the canonical template.
    """
    scripts_dir = tmp_path / ".claude" / "hooks" / "scripts"
    scripts_dir.mkdir(parents=True)
    custom_content = "#!/bin/bash\necho 'my custom'\n"
    existing = scripts_dir / "statusline.sh"
    existing.write_text(custom_content, encoding="utf-8")

    _fake_home_and_run(tmp_path, monkeypatch, force=True)

    updated = existing.read_text(encoding="utf-8")
    assert updated != custom_content, (
        "force=True should replace user-customised statusline.sh"
    )
    assert mod.MPM_MARKER in updated, "Replaced file should contain the MPM marker"


# ---------------------------------------------------------------------------
# 10. Registry: migration is discoverable
# ---------------------------------------------------------------------------


def test_migration_registered_in_registry() -> None:
    """v6_3_1_deploy_claude_assets is present in the MIGRATIONS registry.

    Why: Ensures the migration is actually executed by the runner at startup.
    Test: Scan MIGRATIONS list for the expected id.
    """
    ids = [m.id for m in MIGRATIONS]
    assert "v6_3_1_deploy_claude_assets" in ids, (
        "v6_3_1_deploy_claude_assets must be registered in MIGRATIONS"
    )


def test_migration_callable_via_registry() -> None:
    """The registered migration's run callable is invocable (returns bool).

    Why: Guards against import errors or signature mismatches at registration.
    Test: Find migration in registry; verify run is callable.
    """
    migration = next(
        (m for m in MIGRATIONS if m.id == "v6_3_1_deploy_claude_assets"), None
    )
    assert migration is not None, "Migration not found in registry"
    assert callable(migration.run), "migration.run must be callable"


# ---------------------------------------------------------------------------
# Additional: statusline.sh content contains MPM marker
# ---------------------------------------------------------------------------


def test_deployed_statusline_contains_mpm_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deployed statusline.sh must contain the MPM marker line.

    Why: The marker enables the migration to distinguish MPM-managed copies from
    user-customised copies for future auto-upgrades.
    Test: Deploy; read file; assert marker string is present.
    """
    _fake_home_and_run(tmp_path, monkeypatch)

    content = _deployed_statusline(tmp_path).read_text(encoding="utf-8")
    assert mod.MPM_MARKER in content, (
        f"Deployed statusline.sh must contain MPM marker '{mod.MPM_MARKER}'"
    )
