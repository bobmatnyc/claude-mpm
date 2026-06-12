"""Tests for GitHub issue #804: user-level bundled skill deployment.

Covers:
1. SkillsService.__init__() defaults to USER scope
2. SkillsService(scope=ConfigScope.PROJECT) uses project path
3. Registry _load_user_skills() discovers directory-style skills
4. Registry _load_user_skills() loads legacy flat .md skills
5. Registry _load_project_skills() discovers directory-style skills
6. USER_LEVEL_SKILLS contains all 54 bundled skill names
7. Migration removes project-level bundled skill when user-level exists
8. Migration leaves project-level skill when user-level absent
9. Migration leaves non-bundled custom skills
10. Migration is idempotent
11. deploy_bundled_skills() calls SkillsService(scope=ConfigScope.USER)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BUNDLED_SKILL_NAMES: frozenset[str] = frozenset(
    {
        "artifacts-builder",
        "brainstorming",
        "build-mcp-server",
        "condition-based-waiting",
        "cross-source-research",
        "desktop-applications",
        "dispatching-parallel-agents",
        "end-of-session",
        "env-manager",
        "espocrm-development",
        "finding-duplicate-functions",
        "internal-comms",
        "mpm",
        "mpm-adr",
        "mpm-agent-update-workflow",
        "mpm-bug-reporting",
        "mpm-circuit-breaker-enforcement",
        "mpm-config",
        "mpm-delegation-patterns",
        "mpm-doctor",
        "mpm-git-file-tracking",
        "mpm-help",
        "mpm-init",
        "mpm-monitor",
        "mpm-organize",
        "mpm-postmortem",
        "mpm-pr-workflow",
        "mpm-session-management",
        "mpm-session-pause",
        "mpm-session-resume",
        "mpm-status",
        "mpm-teaching-mode",
        "mpm-ticket-view",
        "mpm-ticketing-integration",
        "mpm-tool-usage-guide",
        "mpm-verification-protocols",
        "mpm-version",
        "mpm-workflow",
        "prd-authoring",
        "prep-meeting",
        "requesting-code-review",
        "root-cause-tracing",
        "security-review",
        "session-analyzer",
        "skill-creator",
        "spec-authoring",
        "spec-linked-docs",
        "systematic-debugging",
        "test-driven-development",
        "test-quality-inspector",
        "testing-anti-patterns",
        "verification-before-completion",
        "webapp-testing",
        "writing-plans",
    }
)

MINIMAL_SKILL_MD = """\
---
name: test-skill
description: A test skill
version: "1.0.0"
---
# Test Skill

This is a test skill.
"""


def _make_skill_dir(base: Path, skill_name: str) -> Path:
    """Create a directory-style skill (base/<skill_name>/SKILL.md)."""
    skill_dir = base / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        MINIMAL_SKILL_MD.replace("test-skill", skill_name), encoding="utf-8"
    )
    return skill_dir


def _make_flat_skill(base: Path, skill_name: str) -> Path:
    """Create a legacy flat skill (base/<skill_name>.md)."""
    base.mkdir(parents=True, exist_ok=True)
    skill_file = base / f"{skill_name}.md"
    skill_file.write_text(
        MINIMAL_SKILL_MD.replace("test-skill", skill_name), encoding="utf-8"
    )
    return skill_file


# ---------------------------------------------------------------------------
# Test 1: SkillsService defaults to USER scope
# ---------------------------------------------------------------------------


def test_skills_service_defaults_to_user_scope(tmp_path: Path) -> None:
    """SkillsService() with no args should target ~/.claude/skills/ (USER scope).

    Why: Issue #804 requires bundled skills deploy at user level by default.
    Test: Monkeypatch Path.home() and assert deployed_skills_path == home/.claude/skills/.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch("pathlib.Path.home", return_value=fake_home):
        from claude_mpm.skills.skills_service import SkillsService

        svc = SkillsService()
        assert svc.deployed_skills_path == fake_home / ".claude" / "skills"


# ---------------------------------------------------------------------------
# Test 2: SkillsService(scope=PROJECT) uses project path
# ---------------------------------------------------------------------------


def test_skills_service_project_scope(tmp_path: Path) -> None:
    """SkillsService(scope=PROJECT) should target {project_root}/.claude/skills/.

    Why: PROJECT scope should still work for callers that want per-project deployment.
    Test: Pass scope=ConfigScope.PROJECT and assert deployed_skills_path is project-rooted.
    """
    from claude_mpm.core.config_scope import ConfigScope
    from claude_mpm.skills.skills_service import SkillsService

    svc = SkillsService(scope=ConfigScope.PROJECT)
    assert svc.deployed_skills_path == svc.project_root / ".claude" / "skills"


# ---------------------------------------------------------------------------
# Test 3: Registry _load_user_skills discovers directory-style skills
# ---------------------------------------------------------------------------


def test_registry_load_user_skills_directory_style(tmp_path: Path) -> None:
    """_load_user_skills() must discover <name>/SKILL.md directory-style skills.

    Why: New bundled skill format uses directories; registry must support them.
    Test: Create a tmp user skills dir with a directory-style skill, monkeypatch
    Path.home(), and assert the skill is registered.
    """
    fake_home = tmp_path / "home"
    user_skills = fake_home / ".claude" / "skills"
    _make_skill_dir(user_skills, "my-dir-skill")

    with patch("pathlib.Path.home", return_value=fake_home):
        import importlib

        from claude_mpm.skills import registry as registry_mod

        importlib.reload(registry_mod)
        reg = registry_mod.SkillsRegistry()
        # Force reload skills
        reg.skills = {}
        reg._load_user_skills()

    assert "my-dir-skill" in reg.skills


# ---------------------------------------------------------------------------
# Test 4: Registry _load_user_skills loads legacy flat .md skills
# ---------------------------------------------------------------------------


def test_registry_load_user_skills_flat_md(tmp_path: Path) -> None:
    """_load_user_skills() must still load legacy flat <name>.md files.

    Why: Backward compat — existing user skills in flat format must keep working.
    Test: Create a tmp user skills dir with a flat .md file and assert it loads.
    """
    fake_home = tmp_path / "home"
    user_skills = fake_home / ".claude" / "skills"
    _make_flat_skill(user_skills, "my-flat-skill")

    with patch("pathlib.Path.home", return_value=fake_home):
        from claude_mpm.skills import registry as registry_mod

        reg = registry_mod.SkillsRegistry()
        reg.skills = {}
        reg._load_user_skills()

    assert "my-flat-skill" in reg.skills


# ---------------------------------------------------------------------------
# Test 5: Registry _load_project_skills discovers directory-style skills
# ---------------------------------------------------------------------------


def test_registry_load_project_skills_directory_style(tmp_path: Path) -> None:
    """_load_project_skills() must discover <name>/SKILL.md directory-style skills.

    Why: Project skills can also be directory-style; registry must support them.
    Test: Create a tmp project skills dir, monkeypatch Path.cwd(), and assert skill loads.
    """
    project_skills = tmp_path / ".claude" / "skills"
    _make_skill_dir(project_skills, "my-project-skill")

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        from claude_mpm.skills import registry as registry_mod

        reg = registry_mod.SkillsRegistry()
        reg.skills = {}
        reg._load_project_skills()

    assert "my-project-skill" in reg.skills


# ---------------------------------------------------------------------------
# Test 6: USER_LEVEL_SKILLS contains all 54 bundled skill names
# ---------------------------------------------------------------------------


def test_user_level_skills_contains_all_bundled() -> None:
    """USER_LEVEL_SKILLS must contain all 54 bundled skill names.

    Why: The dedup guard skips project-level deploy only for skills in this set.
    Test: Assert the frozenset is a superset of BUNDLED_SKILL_NAMES.
    """
    from claude_mpm.services.skills.selective_skill_deployer import USER_LEVEL_SKILLS

    missing = BUNDLED_SKILL_NAMES - USER_LEVEL_SKILLS
    assert not missing, f"Missing from USER_LEVEL_SKILLS: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Test 7: Migration removes project-level bundled skill when user-level exists
# ---------------------------------------------------------------------------


def test_migration_removes_project_skill_when_user_copy_exists(tmp_path: Path) -> None:
    """Migration must remove .claude/skills/<name>/ when ~/.claude/skills/<name>/SKILL.md exists.

    Why: Core behavior — clean up duplicates only when safe (user copy confirmed).
    Test: Set up both user-level and project-level copies; run migration; assert project gone.
    """
    fake_home = tmp_path / "home"
    user_skills = fake_home / ".claude" / "skills"
    project_root = tmp_path / "project"
    project_skills = project_root / ".claude" / "skills"

    # Use a real bundled skill name
    skill_name = "session-analyzer"

    # Create user-level copy
    _make_skill_dir(user_skills, skill_name)
    # Create project-level copy
    _make_skill_dir(project_skills, skill_name)

    assert (project_skills / skill_name).exists()

    with (
        patch("pathlib.Path.home", return_value=fake_home),
        patch("pathlib.Path.cwd", return_value=project_root),
    ):
        from claude_mpm.migrations import (
            v6_5_40_remove_project_level_bundled_skills as mig,
        )

        # Patch _get_bundled_skill_names to return our test set
        with patch.object(
            mig, "_get_bundled_skill_names", return_value=frozenset({skill_name})
        ):
            result = mig.run_migration()

    assert result is True
    assert not (project_skills / skill_name).exists(), (
        "Project-level skill should be removed"
    )
    assert (user_skills / skill_name / "SKILL.md").exists(), (
        "User-level skill must remain"
    )


# ---------------------------------------------------------------------------
# Test 8: Migration leaves project skill when user-level absent
# ---------------------------------------------------------------------------


def test_migration_leaves_project_skill_when_no_user_copy(tmp_path: Path) -> None:
    """Migration must NOT remove project skill if user-level copy is absent.

    Why: Safety guard — never delete without confirming user copy exists.
    Test: Create project-level copy but no user copy; run migration; assert project copy remains.
    """
    fake_home = tmp_path / "home"
    user_skills = fake_home / ".claude" / "skills"
    user_skills.mkdir(parents=True, exist_ok=True)

    project_root = tmp_path / "project"
    project_skills = project_root / ".claude" / "skills"
    skill_name = "session-analyzer"
    _make_skill_dir(project_skills, skill_name)

    with (
        patch("pathlib.Path.home", return_value=fake_home),
        patch("pathlib.Path.cwd", return_value=project_root),
    ):
        from claude_mpm.migrations import (
            v6_5_40_remove_project_level_bundled_skills as mig,
        )

        with patch.object(
            mig, "_get_bundled_skill_names", return_value=frozenset({skill_name})
        ):
            result = mig.run_migration()

    assert result is True
    assert (project_skills / skill_name).exists(), (
        "Project skill must NOT be removed without user copy"
    )


# ---------------------------------------------------------------------------
# Test 9: Migration leaves non-bundled custom skills
# ---------------------------------------------------------------------------


def test_migration_leaves_custom_skills(tmp_path: Path) -> None:
    """Migration must never touch non-bundled custom skills.

    Why: Custom user/project skills must never be deleted by migration.
    Test: Create project-level custom skill (not in bundled set); run migration; assert it remains.
    """
    fake_home = tmp_path / "home"
    project_root = tmp_path / "project"
    project_skills = project_root / ".claude" / "skills"
    custom_skill = "my-custom-project-skill"
    _make_skill_dir(project_skills, custom_skill)

    with (
        patch("pathlib.Path.home", return_value=fake_home),
        patch("pathlib.Path.cwd", return_value=project_root),
    ):
        from claude_mpm.migrations import (
            v6_5_40_remove_project_level_bundled_skills as mig,
        )

        # Bundled set does NOT include custom_skill
        with patch.object(
            mig,
            "_get_bundled_skill_names",
            return_value=frozenset({"session-analyzer"}),
        ):
            result = mig.run_migration()

    assert result is True
    assert (project_skills / custom_skill).exists(), "Custom skill must not be removed"


# ---------------------------------------------------------------------------
# Test 10: Migration is idempotent
# ---------------------------------------------------------------------------


def test_migration_idempotent(tmp_path: Path) -> None:
    """Running migration twice must not error and produce same result.

    Why: Migrations may run on every startup; they must be safe to re-run.
    Test: Run migration twice; assert both return True and project skill removed.
    """
    fake_home = tmp_path / "home"
    user_skills = fake_home / ".claude" / "skills"
    project_root = tmp_path / "project"
    project_skills = project_root / ".claude" / "skills"
    skill_name = "session-analyzer"

    _make_skill_dir(user_skills, skill_name)
    _make_skill_dir(project_skills, skill_name)

    with (
        patch("pathlib.Path.home", return_value=fake_home),
        patch("pathlib.Path.cwd", return_value=project_root),
    ):
        from claude_mpm.migrations import (
            v6_5_40_remove_project_level_bundled_skills as mig,
        )

        with patch.object(
            mig, "_get_bundled_skill_names", return_value=frozenset({skill_name})
        ):
            result1 = mig.run_migration()
            result2 = mig.run_migration()

    assert result1 is True
    assert result2 is True
    assert not (project_skills / skill_name).exists()


# ---------------------------------------------------------------------------
# Test 11: deploy_bundled_skills() uses ConfigScope.USER
# ---------------------------------------------------------------------------


def test_deploy_bundled_skills_uses_user_scope(tmp_path: Path) -> None:
    """deploy_bundled_skills() must instantiate SkillsService(scope=ConfigScope.USER).

    Why: Issue #804 core requirement — startup deployment goes to user level.
    Test: Mock SkillsService in skills_service module and assert it was called
    with scope=ConfigScope.USER. The function imports SkillsService locally from
    claude_mpm.skills.skills_service, so that is the correct patch target.
    """
    from claude_mpm.core.config_scope import ConfigScope

    captured_kwargs: dict = {}

    original_init_called = False

    class MockSkillsService:
        def __init__(self, scope: ConfigScope = ConfigScope.USER) -> None:
            captured_kwargs["scope"] = scope

        def deploy_bundled_skills(self):
            return {"deployed": [], "skipped": [], "errors": []}

    with patch("claude_mpm.skills.skills_service.SkillsService", MockSkillsService):
        # Also patch guards so we reach the SkillsService instantiation
        with (
            patch(
                "claude_mpm.cli.startup._is_bundled_skills_sync_fresh",
                return_value=False,
            ),
            patch(
                "claude_mpm.cli.startup._is_claude_mpm_plugin_installed",
                return_value=False,
            ),
        ):
            from claude_mpm.cli import startup

            # Patch config loader to avoid file system access
            mock_config_loader = MagicMock()
            mock_config_loader.load_main_config.return_value = {}
            with patch(
                "claude_mpm.core.shared.config_loader.ConfigLoader",
                return_value=mock_config_loader,
            ):
                try:
                    startup.deploy_bundled_skills(force_deploy=True)
                except Exception:
                    pass  # Allowed — we only care about SkillsService call args

    assert captured_kwargs.get("scope") == ConfigScope.USER, (
        f"Expected scope=ConfigScope.USER, got {captured_kwargs.get('scope')}"
    )
