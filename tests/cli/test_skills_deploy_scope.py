"""Unit tests for ``claude-mpm skills deploy --scope`` routing.

Verifies that ``SkillsManagementCommand._deploy_skills`` honors ``args.scope``
(issue #806):

- ``--scope user``    -> ``GitSkillSourceManager.deploy_skills`` (~/.claude/skills/)
- ``--scope project`` -> ``GitSkillSourceManager.deploy_skills_to_project``
- no flag (defaults to project) -> ``deploy_skills_to_project``

The handler was previously hardcoded to project-local deployment, silently
ignoring ``--scope user``.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from claude_mpm.cli.commands.skills import SkillsManagementCommand


def _make_args(scope=None, force=False, skills=None):
    """Build a deploy args namespace; omit ``scope`` entirely when None."""
    kwargs = {"force": force, "skills": skills}
    if scope is not None:
        kwargs["scope"] = scope
    return SimpleNamespace(**kwargs)


def _patched_manager():
    """Patch the manager + config classes and return the manager mock.

    The patch targets the symbols at their definition modules because
    ``_deploy_skills`` imports them lazily inside the function body.
    """
    sync_return = {"sources": {}}

    manager = MagicMock()
    manager.sync_all_sources.return_value = sync_return
    manager.deploy_skills_to_project.return_value = {
        "deployed": ["alpha"],
        "updated": [],
        "skipped": [],
        "failed": [],
        "deployment_dir": "/proj/.claude-mpm/skills",
    }
    manager.deploy_skills.return_value = {
        "deployed_count": 1,
        "deployed_skills": ["alpha"],
        "skipped_count": 0,
        "skipped_skills": [],
        "errors": [],
    }
    return manager


def test_scope_user_routes_to_user_level_deploy():
    """``--scope user`` deploys via ``deploy_skills`` to ~/.claude/skills/."""
    manager = _patched_manager()

    with (
        patch(
            "claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager",
            return_value=manager,
        ),
        patch("claude_mpm.config.skill_sources.SkillSourceConfiguration"),
    ):
        result = SkillsManagementCommand()._deploy_skills(_make_args(scope="user"))

    assert result.success is True
    assert result.exit_code == 0

    manager.deploy_skills.assert_called_once()
    manager.deploy_skills_to_project.assert_not_called()

    # User-level deploy must target ~/.claude/skills/.
    _, kwargs = manager.deploy_skills.call_args
    assert kwargs["target_dir"] == Path.home() / ".claude" / "skills"


def test_scope_project_routes_to_project_level_deploy():
    """``--scope project`` deploys via ``deploy_skills_to_project``."""
    manager = _patched_manager()

    with (
        patch(
            "claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager",
            return_value=manager,
        ),
        patch("claude_mpm.config.skill_sources.SkillSourceConfiguration"),
    ):
        result = SkillsManagementCommand()._deploy_skills(_make_args(scope="project"))

    assert result.success is True
    assert result.exit_code == 0

    manager.deploy_skills_to_project.assert_called_once()
    manager.deploy_skills.assert_not_called()


def test_default_scope_is_project():
    """Omitting ``--scope`` defaults to project-level deployment."""
    manager = _patched_manager()

    with (
        patch(
            "claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager",
            return_value=manager,
        ),
        patch("claude_mpm.config.skill_sources.SkillSourceConfiguration"),
    ):
        result = SkillsManagementCommand()._deploy_skills(_make_args(scope=None))

    assert result.success is True
    manager.deploy_skills_to_project.assert_called_once()
    manager.deploy_skills.assert_not_called()


def test_scope_user_passes_skill_filter():
    """``--skill`` selections are forwarded as a ``skill_filter`` set."""
    manager = _patched_manager()

    with (
        patch(
            "claude_mpm.services.skills.git_skill_source_manager.GitSkillSourceManager",
            return_value=manager,
        ),
        patch("claude_mpm.config.skill_sources.SkillSourceConfiguration"),
    ):
        SkillsManagementCommand()._deploy_skills(
            _make_args(scope="user", skills=["alpha", "beta"])
        )

    _, kwargs = manager.deploy_skills.call_args
    assert kwargs["skill_filter"] == {"alpha", "beta"}
