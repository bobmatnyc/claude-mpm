"""Tests for the statusline opt-out / override knob.

Covers the three ways a user can stop claude-mpm from injecting its
per-project ``statusLine`` entry (or point it at a custom command):

1. Environment variable ``CLAUDE_MPM_STATUSLINE``.
2. User/project ``statusline`` section in ``.claude-mpm/configuration.yaml``.
3. Default (nothing set) — behavior must be unchanged from before this knob
   existed.

Also covers precedence (env beats config) and the critical no-op guarantee:
when disabled, ``run_migration`` must not create the managed script, must not
add/modify a ``statusLine`` entry, and must not touch an existing one either.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

import claude_mpm.migrations.migrate_statusline_autoconfig as autoconfig_mod
from claude_mpm.migrations.migrate_statusline_autoconfig import (
    StatuslinePolicyKind,
    _is_mpm_owned_statusline,
    _resolve_statusline_policy,
)

ENV_VAR = autoconfig_mod.STATUSLINE_ENV_VAR
MPM_KEY = autoconfig_mod._MPM_OWNED_KEY


def _write_user_config(home: Path, content: str) -> None:
    config_path = home / ".claude-mpm" / "config" / "configuration.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(content, encoding="utf-8")


def _write_project_config(project_dir: Path, content: str) -> None:
    config_path = project_dir / ".claude-mpm" / "configuration.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(content, encoding="utf-8")


def _project_settings_path(project_dir: Path) -> Path:
    return project_dir / ".claude" / "settings.json"


def _read_settings(project_dir: Path) -> dict:
    return json.loads(_project_settings_path(project_dir).read_text(encoding="utf-8"))


def _write_settings(project_dir: Path, settings: dict) -> None:
    path = _project_settings_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def _stop_hook_commands(settings: dict) -> list[str]:
    """Flatten every Stop hook command string in a settings dict."""
    commands: list[str] = []
    for group in settings.get("hooks", {}).get("Stop", []) or []:
        for hook in group.get("hooks", []) or []:
            command = hook.get("command")
            if isinstance(command, str):
                commands.append(command)
    return commands


# ---------------------------------------------------------------------------
# 1. Environment variable
# ---------------------------------------------------------------------------


def test_env_off_disables(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """CLAUDE_MPM_STATUSLINE=off resolves to DISABLED.

    Why: The env var is the highest-precedence, simplest opt-out mechanism.
    Test: Set the env var to each accepted disable spelling; assert DISABLED.
    """
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    for value in ("off", "OFF", "false", "False", "0", "disabled", "none", " off "):
        monkeypatch.setenv(ENV_VAR, value)
        policy = _resolve_statusline_policy(tmp_path / "project")
        assert policy.kind is StatuslinePolicyKind.DISABLED, f"value={value!r}"


def test_env_custom_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A non-disable, non-empty CLAUDE_MPM_STATUSLINE value is a custom command.

    Why: Lets a user point claude-mpm at their own statusline script entirely
    via a single env var, without editing YAML.
    Test: Set the env var to an arbitrary command string; assert CUSTOM with
    that exact command.
    """
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    monkeypatch.setenv(ENV_VAR, "/usr/local/bin/my-statusline.sh")
    policy = _resolve_statusline_policy(tmp_path / "project")
    assert policy.kind is StatuslinePolicyKind.CUSTOM
    assert policy.command == "/usr/local/bin/my-statusline.sh"


# ---------------------------------------------------------------------------
# 2. Config file
# ---------------------------------------------------------------------------


def test_config_enabled_false_disables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """statusline.enabled: false in user configuration.yaml resolves to DISABLED.

    Why: Supports users who prefer a persistent config-file opt-out over an
    env var (e.g. because they don't control their shell's env in every
    terminal they open Claude Code from).
    Test: Write ``statusline: {enabled: false}`` to the user config; assert
    DISABLED.
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    _write_user_config(home, "statusline:\n  enabled: false\n")

    policy = _resolve_statusline_policy(tmp_path / "project")
    assert policy.kind is StatuslinePolicyKind.DISABLED


def test_config_command_is_custom(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """statusline.command in configuration.yaml resolves to CUSTOM.

    Test: Write ``statusline: {command: "..."}`` to the user config; assert
    CUSTOM with that command.
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    _write_user_config(home, 'statusline:\n  command: "~/bin/statusline.sh"\n')

    policy = _resolve_statusline_policy(tmp_path / "project")
    assert policy.kind is StatuslinePolicyKind.CUSTOM
    assert policy.command == "~/bin/statusline.sh"


def test_project_config_overlays_user_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Project-level configuration.yaml overrides the user-level one.

    Why: Mirrors the existing per-agent model config overlay pattern (user
    config first, project config wins for duplicate keys) so one project can
    use a different custom command than the user's global default.
    Test: Set a custom command at user level, a different one at project
    level; assert the project-level value wins.
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    _write_user_config(home, 'statusline:\n  command: "~/bin/global-status.sh"\n')
    _write_project_config(project_dir, 'statusline:\n  command: "./tools/status.sh"\n')

    policy = _resolve_statusline_policy(project_dir)
    assert policy.kind is StatuslinePolicyKind.CUSTOM
    assert policy.command == "./tools/status.sh"


def test_project_config_enabled_false_wins_over_user_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A project-level explicit disable wins over a user-level custom command.

    Why: Documents and locks in the precedence rule inside
    ``_load_statusline_config``: keys are merged individually with the
    project value winning per-key, and ``_resolve_statusline_policy`` checks
    ``enabled`` before ``command`` in the merged result — so an explicit
    project-level disable always beats any command, from either level.
    Test: Set a custom command at user level, ``enabled: false`` at project
    level; assert DISABLED.
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    _write_user_config(home, 'statusline:\n  command: "~/bin/global-status.sh"\n')
    _write_project_config(project_dir, "statusline:\n  enabled: false\n")

    policy = _resolve_statusline_policy(project_dir)
    assert policy.kind is StatuslinePolicyKind.DISABLED


# ---------------------------------------------------------------------------
# 3. Precedence: env beats config
# ---------------------------------------------------------------------------


def test_env_beats_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """CLAUDE_MPM_STATUSLINE takes precedence over configuration.yaml.

    Why: The env var is documented as the highest-precedence override; it must
    win even when a config file explicitly requests different behavior.
    Test: Set config to a custom command, set env var to 'off'; assert the
    resolved policy is DISABLED (the env var value), not CUSTOM.
    """
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    _write_user_config(home, 'statusline:\n  command: "/should/not/win"\n')
    monkeypatch.setenv(ENV_VAR, "off")

    policy = _resolve_statusline_policy(tmp_path / "project")
    assert policy.kind is StatuslinePolicyKind.DISABLED


# ---------------------------------------------------------------------------
# 4. Default unchanged
# ---------------------------------------------------------------------------


def test_default_is_managed_when_nothing_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no env var and no config file, the policy is MANAGED (unchanged).

    Why: Regression guard for backward compatibility — the vast majority of
    users have never heard of this knob and must see identical behavior.
    Test: Clear the env var, use a home dir with no config file; assert
    MANAGED.
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    policy = _resolve_statusline_policy(tmp_path / "project")
    assert policy.kind is StatuslinePolicyKind.MANAGED


def test_run_migration_default_behavior_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With nothing configured, run_migration behaves exactly as before.

    Test: Run the migration against an empty project dir with no env var and
    no config file; assert the managed script and the default statusLine
    entry are both created.
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    script_path = tmp_path / "home" / ".claude" / "hooks" / "scripts" / "statusline.sh"
    assert script_path.exists(), "managed script must still be created by default"

    settings = json.loads(
        (project_dir / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    assert "statusline.sh" in settings["statusLine"]["command"]


# ---------------------------------------------------------------------------
# 5. DISABLED is a pure no-op
# ---------------------------------------------------------------------------


def test_disabled_does_not_touch_existing_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DISABLED must not create, modify, or delete anything.

    Why: The core safety guarantee of the opt-out — it must be indistinguishable
    from claude-mpm never having run at all, and must never delete a user's
    pre-existing statusLine entry either.
    Test: Seed a project settings.json with a user-authored statusLine entry;
    run the migration with the knob disabled; assert settings.json is
    byte-for-byte unchanged and the managed script is never created.
    """
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setenv(ENV_VAR, "off")

    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    settings_path = claude_dir / "settings.json"
    original_content = json.dumps(
        {"statusLine": {"type": "command", "command": "/my/own/script.sh"}},
        indent=2,
    )
    settings_path.write_text(original_content, encoding="utf-8")

    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    assert settings_path.read_text(encoding="utf-8") == original_content, (
        "settings.json must be byte-for-byte unchanged when disabled"
    )
    script_path = home / ".claude" / "hooks" / "scripts" / "statusline.sh"
    assert not script_path.exists(), "managed script must not be created when disabled"


def test_disabled_does_not_create_settings_file_in_fresh_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DISABLED must not create settings.json at all in a brand-new project.

    Why: This is the exact scenario the knob exists for — a brand-new project
    with no ``.claude/`` directory must stay untouched.
    Test: Run the migration against an empty project dir with the knob
    disabled; assert no ``.claude`` directory (and no managed script) is
    created at all.
    """
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setenv(ENV_VAR, "off")

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    assert not (project_dir / ".claude").exists(), (
        "no .claude directory should be created when disabled"
    )
    assert not (home / ".claude" / "hooks" / "scripts" / "statusline.sh").exists()


def test_disabled_removed_then_run_migration_writes_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Sanity check: with the knob removed, the same call DOES write the entry.

    Why: Proves the no-op tests above are meaningful — they demonstrate the
    absence of a write specifically because of the knob, not because of some
    unrelated bug that would make run_migration a no-op regardless.
    Test: Run twice against a fresh project dir: once with the env var set to
    'off' (no settings.json expected), once with it cleared (settings.json
    with a statusLine entry expected).
    """
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    monkeypatch.setenv(ENV_VAR, "off")
    autoconfig_mod.run_migration(installation_dir=project_dir)
    assert not (project_dir / ".claude" / "settings.json").exists()

    monkeypatch.delenv(ENV_VAR, raising=False)
    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True
    assert (project_dir / ".claude" / "settings.json").exists()


# ---------------------------------------------------------------------------
# 6. CUSTOM writes the override command instead of the bundled script
# ---------------------------------------------------------------------------


def test_custom_command_written_instead_of_bundled_script(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """CUSTOM policy writes the override command and skips the bundled script.

    Test: Set the env var to a custom command; run the migration against a
    fresh project; assert settings.json's statusLine.command is the custom
    command (not the bundled script path) and the bundled script is never
    created.
    """
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setenv(ENV_VAR, "/opt/my/statusline")

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    settings = json.loads(
        (project_dir / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    assert settings["statusLine"]["command"] == "/opt/my/statusline"
    script_path = home / ".claude" / "hooks" / "scripts" / "statusline.sh"
    assert not script_path.exists(), "bundled script must not be created under CUSTOM"


# ---------------------------------------------------------------------------
# 8. Explicit ownership marker (entries MPM writes stay recognisable to MPM)
# ---------------------------------------------------------------------------


def test_is_mpm_owned_statusline_predicate() -> None:
    """Ownership is the recorded marker, with the legacy command as a fallback.

    Why: This predicate is the whole ownership model. Marker present means we
    wrote it whatever the command says; marker absent falls back to the legacy
    ``statusline.sh`` signal so pre-marker entries are still adopted; neither
    means the entry is user-authored and must not be touched.
    Test: One case per branch, including a marker-bearing entry whose command
    is a completely unrelated path.
    """
    assert _is_mpm_owned_statusline(
        {"type": "command", "command": "/opt/totally/unrelated", MPM_KEY: True}
    ), "an entry carrying the marker is ours regardless of its command"

    assert _is_mpm_owned_statusline(
        {"type": "command", "command": ".claude/hooks/scripts/statusline.sh"}
    ), "a pre-marker entry pointing at the bundled script is still ours"

    assert not _is_mpm_owned_statusline(
        {"type": "command", "command": "/my/own/bar.sh"}
    ), "no marker and a non-bundled command means user-authored"

    assert not _is_mpm_owned_statusline(None)
    assert not _is_mpm_owned_statusline("not-a-dict")


def test_custom_command_change_is_applied_on_next_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Changing the custom command must actually change the written entry.

    Why: Regression test for the ownership bug this marker exists to fix.
    Ownership used to be inferred from the command string containing
    ``statusline.sh``.  Under CUSTOM, MPM writes the *user's* command, which
    does not contain that substring — so on the next run MPM looked at an entry
    it had written itself, failed to recognise it, classified it as
    user-authored and refused to touch it.  Net effect: the first custom
    command ever written froze permanently and every later change to
    ``CLAUDE_MPM_STATUSLINE`` was silently ignored, with no error and no log.
    Test: Run with custom command A, then again with a different command B;
    assert the entry ends up as B.
    """
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    monkeypatch.setenv(ENV_VAR, "/opt/mybar-a")
    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True
    assert _read_settings(project_dir)["statusLine"]["command"] == "/opt/mybar-a"

    monkeypatch.setenv(ENV_VAR, "/opt/mybar-b")
    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    entry = _read_settings(project_dir)["statusLine"]
    assert entry["command"] == "/opt/mybar-b", (
        "a changed custom command must be written, not silently ignored"
    )
    assert entry[MPM_KEY] is True, "MPM-written entries must carry the marker"


def test_legacy_marker_less_entry_is_adopted_and_updated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An entry from an older MPM version (no marker) is still MPM-owned.

    Why: Backward compatibility is a hard requirement — installs predating the
    marker must keep self-healing, so the legacy ``statusline.sh`` command
    substring is retained as an ownership fallback.
    Test: Seed a legacy project-relative MPM entry with no marker; run MANAGED;
    assert the command is upgraded to the absolute bundled path and the marker
    is now stamped so the next run recognises it directly.
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    _write_settings(
        project_dir,
        {
            "statusLine": {
                "type": "command",
                "command": ".claude/hooks/scripts/statusline.sh",
            }
        },
    )

    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    entry = _read_settings(project_dir)["statusLine"]
    assert entry["command"] == str(autoconfig_mod._USER_SCRIPT_PATH)
    assert entry[MPM_KEY] is True, "adopting a legacy entry must stamp the marker"


def test_user_authored_entry_left_untouched_under_managed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A genuinely user-authored statusLine entry is never overwritten.

    Why: Guards against regressing the entire point of this PR — respecting a
    user's own statusline.  Making ownership explicit must not widen what MPM
    considers its own.
    Test: Seed an entry with no marker and a non-bundled command; run MANAGED;
    assert the entry is unchanged and not retroactively marked as ours.
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    user_entry = {"type": "command", "command": "/my/own/bar.sh", "padding": 0}
    _write_settings(project_dir, {"statusLine": dict(user_entry)})

    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    assert _read_settings(project_dir)["statusLine"] == user_entry


def test_user_authored_entry_left_untouched_under_custom(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CUSTOM policy also respects a user-authored entry.

    Test: Seed a marker-less, non-bundled entry; run with a custom command
    configured; assert the seeded entry survives unchanged.
    """
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    monkeypatch.setenv(ENV_VAR, "/opt/mybar")
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    user_entry = {"type": "command", "command": "/my/own/bar.sh"}
    _write_settings(project_dir, {"statusLine": dict(user_entry)})

    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    assert _read_settings(project_dir)["statusLine"] == user_entry


# ---------------------------------------------------------------------------
# 9. MANAGED -> CUSTOM retracts the now-stale --clear Stop hook
# ---------------------------------------------------------------------------


def test_managed_to_custom_removes_stale_mpm_stop_hook(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Switching to CUSTOM removes the MPM ``--clear`` hook but keeps user hooks.

    Why: The Stop hook exists only to blank the bar painted by the bundled
    ``statusline.sh``.  Once ``statusLine.command`` points at a custom command,
    a hook left over from an earlier MANAGED run is firing ``--clear`` against a
    script that is no longer the active statusline.  We still never *install* a
    ``--clear`` hook for a custom command, but we must retract our own.
    Test: Run MANAGED (installing the hook), add a user-owned Stop hook beside
    it, then run CUSTOM; assert the ``--clear`` hook is gone, the user hook
    survives, and statusLine points at the custom command.
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True
    settings = _read_settings(project_dir)
    assert any("--clear" in cmd for cmd in _stop_hook_commands(settings)), (
        "precondition: MANAGED must have installed the --clear Stop hook"
    )

    # Seed a user-owned Stop hook alongside the MPM one.
    settings["hooks"]["Stop"][0]["hooks"].append(
        {"type": "command", "command": "/my/own/on-stop.sh"}
    )
    _write_settings(project_dir, settings)

    monkeypatch.setenv(ENV_VAR, "/opt/mybar")
    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    settings = _read_settings(project_dir)
    commands = _stop_hook_commands(settings)
    assert not any("--clear" in cmd for cmd in commands), (
        f"stale MPM --clear Stop hook must be removed, got {commands}"
    )
    assert "/my/own/on-stop.sh" in commands, "user-owned Stop hook must survive"
    assert settings["statusLine"]["command"] == "/opt/mybar"


def test_custom_does_not_remove_user_owned_stop_hooks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """CUSTOM must not touch Stop hooks MPM never installed.

    Why: The removal path is destructive, so it must be tightly scoped to the
    hook MPM itself wrote.
    Test: Seed a project with only user-authored Stop hooks; run CUSTOM; assert
    every seeded hook survives.
    """
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    monkeypatch.setenv(ENV_VAR, "/opt/mybar")
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    _write_settings(
        project_dir,
        {
            "hooks": {
                "Stop": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"type": "command", "command": "/my/own/on-stop.sh"},
                            {"type": "command", "command": "/my/own/other.sh --clear"},
                        ],
                    }
                ]
            }
        },
    )

    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    commands = _stop_hook_commands(_read_settings(project_dir))
    assert commands == ["/my/own/on-stop.sh", "/my/own/other.sh --clear"]


def test_custom_still_runs_global_settings_self_heal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """CUSTOM runs the issue #924 global self-heal before its early return.

    Why: DISABLED is the *only* policy exempt from the global-settings
    self-heal.  A CUSTOM policy means the bundled statusline is not the active
    statusline anywhere, so an MPM-owned entry left in the shared
    ``~/.claude/settings.json`` by a pre-#924 install is stale by definition and
    must still be stripped.  The CUSTOM early return sits *after* the cleanup
    call, so this holds — this test pins that ordering, which is otherwise easy
    to break by moving the ``if policy.kind is CUSTOM`` branch upward.
    Test: Seed a pre-#924 global install (MPM-owned statusLine plus a
    ``--clear`` Stop hook) alongside a user-owned Stop hook, run the migration
    under CUSTOM, and assert the MPM-owned global entries are gone, the
    user-owned hook survives, and the project-local entry got the custom
    command.
    """
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    global_settings = home / ".claude" / "settings.json"
    global_settings.parent.mkdir(parents=True)
    global_settings.write_text(
        json.dumps(
            {
                "statusLine": {
                    "type": "command",
                    "command": "/legacy/statusline.sh",
                },
                "hooks": {
                    "Stop": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "/legacy/statusline.sh --clear",
                                },
                                {"type": "command", "command": "/my/own/on-stop.sh"},
                            ],
                        }
                    ]
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv(ENV_VAR, "/opt/mybar")
    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    global_data = json.loads(global_settings.read_text(encoding="utf-8"))
    assert "statusLine" not in global_data, (
        "stale MPM-owned global statusLine must be stripped under CUSTOM too"
    )
    assert _stop_hook_commands(global_data) == ["/my/own/on-stop.sh"], (
        "the global --clear hook must go; the user's own Stop hook must stay"
    )
    assert _read_settings(project_dir)["statusLine"]["command"] == "/opt/mybar"


# ---------------------------------------------------------------------------
# 7. update-statusline --force still respects DISABLED
# ---------------------------------------------------------------------------


def test_force_true_does_not_override_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """force=True (as used by ``update-statusline --force``) must not bypass DISABLED.

    Why: A user who explicitly opted out should not have that choice silently
    reversed by an unrelated maintenance command.
    Test: Set the knob to disabled; call run_migration(force=True); assert it
    is still a no-op (no script, no settings.json).
    """
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setenv(ENV_VAR, "off")

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    assert (
        autoconfig_mod.run_migration(installation_dir=project_dir, force=True) is True
    )

    assert not (project_dir / ".claude").exists()
    assert not (home / ".claude" / "hooks" / "scripts" / "statusline.sh").exists()


def test_disabled_does_not_touch_global_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DISABLED short-circuits before the global-settings self-heal pass.

    Why: ``_cleanup_global_statusline_settings`` mutates the shared
    ``~/.claude/settings.json``.  An opt-out must be indistinguishable from
    claude-mpm never having run, which means the early return has to precede
    that cleanup — even though the entries it would strip are ones MPM wrote.
    Test: Seed a global settings.json containing an MPM-owned statusLine and a
    ``--clear`` Stop hook; run the migration with the knob disabled; assert the
    global file is byte-for-byte unchanged.
    """
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.setenv(ENV_VAR, "off")

    global_settings = home / ".claude" / "settings.json"
    global_settings.parent.mkdir(parents=True)
    original = json.dumps(
        {
            "statusLine": {
                "type": "command",
                "command": "/somewhere/statusline.sh",
                MPM_KEY: True,
            },
            "hooks": {
                "Stop": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"type": "command", "command": "statusline.sh --clear"}
                        ],
                    }
                ]
            },
        },
        indent=2,
    )
    global_settings.write_text(original, encoding="utf-8")

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    assert autoconfig_mod.run_migration(installation_dir=project_dir) is True

    assert global_settings.read_text(encoding="utf-8") == original, (
        "global settings.json must be byte-for-byte unchanged when disabled"
    )
