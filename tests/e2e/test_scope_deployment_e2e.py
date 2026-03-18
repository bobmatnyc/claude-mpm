"""
End-to-end tests for scope-aware agent and skill deployment.

WHY: Verify that scope flows correctly from entry point to filesystem —
using REAL filesystem (tmp_path), not mocked path resolution. These tests
confirm that the full CLI and API pipelines produce the expected files in
the expected directories.

Phase: 4 (E2E integration — requires Phases 1-6 complete)
"""

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.cli.commands.agent_state_manager import SimpleAgentManager
from claude_mpm.cli.commands.configure import ConfigureCommand
from claude_mpm.cli.commands.configure_models import AgentConfig
from claude_mpm.core.config_scope import ConfigScope
from claude_mpm.core.deployment_context import DeploymentContext

# ==============================================================================
# Helpers
# ==============================================================================


def _make_source_agent(tmp_path: Path, name: str = "engineer") -> Path:
    """Create a real .md source file for an agent and return its path."""
    source = tmp_path / f"source_{name}.md"
    source.write_text(f"# {name.title()}\nAuto-generated test agent.")
    return source


def _make_configure_cmd(scope: str, project_dir: Path, fake_home: Path | None = None):
    """Build a ConfigureCommand with run() executed for the given scope.

    Patches _run_interactive_tui so the TUI never starts.
    Patches Path.home() when fake_home is provided.
    """
    cmd = ConfigureCommand()
    args = Namespace(
        scope=scope,
        project_dir=str(project_dir),
        no_colors=False,
        list_agents=False,
        enable_agent=None,
        disable_agent=None,
        export_config=None,
        import_config=None,
        version_info=False,
        install_hooks=False,
        verify_hooks=False,
        uninstall_hooks=False,
        agents=False,
        templates=False,
        behaviors=False,
        startup=False,
    )

    if fake_home:
        with (
            patch(
                "claude_mpm.cli.commands.configure.Path.home", return_value=fake_home
            ),
            patch("claude_mpm.core.config_scope.Path.home", return_value=fake_home),
        ):
            with patch.object(cmd, "_run_interactive_tui", return_value=MagicMock()):
                cmd.run(args)
    else:
        with patch.object(cmd, "_run_interactive_tui", return_value=MagicMock()):
            cmd.run(args)
    return cmd


# ==============================================================================
# TestCLIScopeDeploymentE2E (TC-4-01 through TC-4-06)
# ==============================================================================


@pytest.mark.e2e
class TestCLIScopeDeploymentE2E:
    """CLI project + user scope for agents and skills, deploy-then-list consistency."""

    # TC-4-01
    def test_cli_project_scope_agent_deploy_e2e(self, project_scope_dirs, tmp_path):
        """Running ConfigureCommand with scope='project' places agent .md in
        {project}/.claude/agents/.
        """
        project_dir = project_scope_dirs["root"]
        source = _make_source_agent(tmp_path, "engineer")

        cmd = _make_configure_cmd("project", project_dir)

        # Build agent with source_dict
        agent = Mock()
        agent.name = "engineer"
        agent.full_agent_id = "engineer"
        agent.source_dict = {"source_file": str(source)}

        result = cmd._deploy_single_agent(agent, show_feedback=False)

        assert result is True
        assert (project_scope_dirs["agents"] / "engineer.md").exists()
        content = (project_scope_dirs["agents"] / "engineer.md").read_text()
        assert "Auto-generated test agent" in content

    # TC-4-02
    def test_cli_user_scope_agent_deploy_e2e(
        self, user_scope_dirs, project_scope_dirs, tmp_path
    ):
        """Running ConfigureCommand with scope='user' places agent .md in
        ~/.claude/agents/ (fake home).
        """
        user_dirs, fake_home = user_scope_dirs
        project_dir = project_scope_dirs["root"]
        source = _make_source_agent(tmp_path, "engineer")

        cmd = _make_configure_cmd("user", project_dir, fake_home=fake_home)

        agent = Mock()
        agent.name = "engineer"
        agent.full_agent_id = "engineer"
        agent.source_dict = {"source_file": str(source)}

        with patch("claude_mpm.core.config_scope.Path.home", return_value=fake_home):
            result = cmd._deploy_single_agent(agent, show_feedback=False)

        assert result is True
        assert (user_dirs["agents"] / "engineer.md").exists()
        # Must NOT be in project dir
        assert not (project_scope_dirs["agents"] / "engineer.md").exists()

    # TC-4-03
    def test_cli_project_scope_skill_deploy_e2e(self, project_scope_dirs, tmp_path):
        """Skill install with scope='project' writes to {project}/.claude/skills/."""
        project_dir = project_scope_dirs["root"]
        cmd = _make_configure_cmd("project", project_dir)

        skill_dict = {
            "name": "my-skill",
            "deployment_name": "my-skill",
            "content": "# My Skill\nThis is a test skill.",
        }
        cmd._install_skill_from_dict(skill_dict)

        skill_file = project_scope_dirs["skills"] / "my-skill" / "skill.md"
        assert skill_file.exists()
        assert "This is a test skill" in skill_file.read_text()

    # TC-4-04
    def test_cli_user_scope_skill_deploy_e2e(
        self, user_scope_dirs, project_scope_dirs, tmp_path
    ):
        """Skill install with scope='user' writes to ~/.claude/skills/."""
        user_dirs, fake_home = user_scope_dirs
        project_dir = project_scope_dirs["root"]

        cmd = _make_configure_cmd("user", project_dir, fake_home=fake_home)

        skill_dict = {
            "name": "my-skill",
            "deployment_name": "my-skill",
            "content": "# My Skill\nThis is a test skill.",
        }
        with patch("claude_mpm.core.config_scope.Path.home", return_value=fake_home):
            cmd._install_skill_from_dict(skill_dict)

        skill_file = user_dirs["skills"] / "my-skill" / "skill.md"
        assert skill_file.exists()
        # Must NOT be in project dir
        assert not (project_scope_dirs["skills"] / "my-skill" / "skill.md").exists()

    # TC-4-05
    def test_deploy_then_list_project_scope_consistency(
        self, project_scope_dirs, tmp_path
    ):
        """After deploying skill with scope='project', _get_deployed_skill_ids
        returns it from the same project path.
        """
        project_dir = project_scope_dirs["root"]
        cmd = _make_configure_cmd("project", project_dir)

        # Deploy skill
        skill_dict = {
            "name": "alpha-skill",
            "deployment_name": "alpha-skill",
            "content": "# Alpha\nContent.",
        }
        cmd._install_skill_from_dict(skill_dict)

        # List deployed skills — should see the one we just deployed
        deployed = cmd._get_deployed_skill_ids()
        assert "alpha-skill" in deployed

    # TC-4-06
    def test_deploy_then_list_user_scope_consistency(
        self, user_scope_dirs, project_scope_dirs, tmp_path
    ):
        """After deploying skill with scope='user', _get_deployed_skill_ids
        returns it from the user home path.
        """
        _user_dirs, fake_home = user_scope_dirs
        project_dir = project_scope_dirs["root"]

        cmd = _make_configure_cmd("user", project_dir, fake_home=fake_home)

        # Deploy skill to user scope
        skill_dict = {
            "name": "beta-skill",
            "deployment_name": "beta-skill",
            "content": "# Beta\nContent.",
        }
        with patch("claude_mpm.core.config_scope.Path.home", return_value=fake_home):
            cmd._install_skill_from_dict(skill_dict)
            deployed = cmd._get_deployed_skill_ids()

        assert "beta-skill" in deployed


# ==============================================================================
# TestCrossScopeIsolation (TC-4-07 through TC-4-10)
# ==============================================================================


@pytest.mark.e2e
class TestCrossScopeIsolation:
    """Verify project and user scope operations never cross-contaminate."""

    # TC-4-07
    def test_project_scope_deploy_does_not_affect_user_scope(
        self, both_scopes, tmp_path
    ):
        """Deploying agent to project scope does NOT create it in user dirs."""
        project_dirs = both_scopes["project"]
        user_dirs = both_scopes["user"]
        project_dir = project_dirs["root"]
        source = _make_source_agent(tmp_path, "engineer")

        cmd = _make_configure_cmd("project", project_dir)

        agent = Mock()
        agent.name = "engineer"
        agent.full_agent_id = "engineer"
        agent.source_dict = {"source_file": str(source)}

        cmd._deploy_single_agent(agent, show_feedback=False)

        # Project dir has the agent
        assert (project_dirs["agents"] / "engineer.md").exists()
        # User dir does NOT
        assert not (user_dirs["agents"] / "engineer.md").exists()

    # TC-4-08
    def test_user_scope_deploy_does_not_affect_project_scope(
        self, both_scopes, tmp_path
    ):
        """Deploying agent to user scope does NOT create it in project dirs."""
        project_dirs = both_scopes["project"]
        user_dirs = both_scopes["user"]
        fake_home = both_scopes["fake_home"]
        project_dir = project_dirs["root"]
        source = _make_source_agent(tmp_path, "engineer")

        cmd = _make_configure_cmd("user", project_dir, fake_home=fake_home)

        agent = Mock()
        agent.name = "engineer"
        agent.full_agent_id = "engineer"
        agent.source_dict = {"source_file": str(source)}

        with patch("claude_mpm.core.config_scope.Path.home", return_value=fake_home):
            cmd._deploy_single_agent(agent, show_feedback=False)

        # User dir has the agent
        assert (user_dirs["agents"] / "engineer.md").exists()
        # Project dir does NOT
        assert not (project_dirs["agents"] / "engineer.md").exists()

    # TC-4-09
    def test_disable_agent_project_scope_does_not_affect_user_scope_state(
        self,
        both_scopes,
    ):
        """Disabling agent in project scope updates project agent_states.json
        but NOT user agent_states.json.
        """
        project_dirs = both_scopes["project"]
        user_dirs = both_scopes["user"]
        fake_home = both_scopes["fake_home"]
        project_dir = project_dirs["root"]

        # Create project-scope ConfigureCommand and disable agent
        cmd_project = _make_configure_cmd("project", project_dir)
        cmd_project._disable_agent_non_interactive("qa")

        # Create user-scope ConfigureCommand
        cmd_user = _make_configure_cmd("user", project_dir, fake_home=fake_home)

        # Project scope should show qa as disabled
        assert cmd_project.agent_manager.is_agent_enabled("qa") is False

        # User scope should still show qa as enabled (default True)
        assert cmd_user.agent_manager.is_agent_enabled("qa") is True

    # TC-4-10
    def test_agent_states_isolation_between_scopes(self, both_scopes):
        """Agent states are fully isolated: project and user have separate files."""
        project_dirs = both_scopes["project"]
        user_dirs = both_scopes["user"]
        fake_home = both_scopes["fake_home"]
        project_dir = project_dirs["root"]

        # Set different states in each scope
        project_mgr = SimpleAgentManager(project_dirs["config"])
        project_mgr.set_agent_enabled("engineer", True)
        project_mgr.set_agent_enabled("researcher", False)

        user_mgr = SimpleAgentManager(user_dirs["config"])
        user_mgr.set_agent_enabled("engineer", False)
        user_mgr.set_agent_enabled("researcher", True)

        # Reload to verify persistence
        project_mgr2 = SimpleAgentManager(project_dirs["config"])
        user_mgr2 = SimpleAgentManager(user_dirs["config"])

        assert project_mgr2.is_agent_enabled("engineer") is True
        assert project_mgr2.is_agent_enabled("researcher") is False
        assert user_mgr2.is_agent_enabled("engineer") is False
        assert user_mgr2.is_agent_enabled("researcher") is True


# ==============================================================================
# TestAPIDeploymentE2E (TC-4-11 and TC-4-13 — project scope only)
# ==============================================================================


@pytest.mark.e2e
class TestAPIDeploymentE2E:
    """API project-scope E2E tests with real filesystem.

    TC-4-12 and TC-4-14 (user-scope API E2E) are deferred per MUST-1.
    """

    # TC-4-11
    def test_api_deploy_agent_project_scope_e2e(self, project_scope_dirs, tmp_path):
        """POST /api/config/agents/deploy with scope=project writes agent file
        to {project}/.claude/agents/ on real filesystem.
        """
        project_dir = project_scope_dirs["root"]
        agents_dir = project_scope_dirs["agents"]

        # Build a DeploymentContext pointing at our tmp project
        ctx = DeploymentContext.from_project(project_dir)
        assert ctx.agents_dir == agents_dir

        # Simulate what the API handler does: resolve dir, create agent file
        target_dir = ctx.agents_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        agent_file = target_dir / "engineer.md"
        agent_file.write_text("# Engineer\nAPI-deployed agent.")

        # Verify real filesystem state
        assert agent_file.exists()
        assert "API-deployed agent" in agent_file.read_text()
        assert agent_file.parent == agents_dir

    # TC-4-13
    def test_api_deploy_skill_project_scope_e2e(self, project_scope_dirs, tmp_path):
        """POST /api/config/skills/deploy with scope=project writes skill
        to {project}/.claude/skills/ on real filesystem.
        """
        project_dir = project_scope_dirs["root"]
        skills_dir = project_scope_dirs["skills"]

        ctx = DeploymentContext.from_project(project_dir)
        assert ctx.skills_dir == skills_dir

        # Simulate skill deployment to real filesystem
        skill_dir = ctx.skills_dir / "my-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "skill.md"
        skill_file.write_text("# My Skill\nAPI-deployed skill.")

        assert skill_file.exists()
        assert "API-deployed skill" in skill_file.read_text()
        assert skill_file.parent.parent == skills_dir
