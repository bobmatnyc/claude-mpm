"""Tests for the project-level deployment guard for USER_LEVEL_AGENTS.

These tests verify that no deployment code path writes a CORE
(``USER_LEVEL_AGENTS``) agent into a project's ``.claude/agents/`` directory,
and that a stale project-level copy left over from the earlier routing bug is
cleaned up automatically on the next deploy.

The shared user-level directory (``~/.claude/agents``) must never be modified by
the guard.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.services.agents.deployment.agent_deployment import USER_LEVEL_AGENTS
from claude_mpm.services.agents.deployment.user_level_routing import (
    is_user_level_agent,
    is_user_level_agents_dir,
    skip_project_level_user_agent,
)

CORE_AGENT = "engineer"  # A stable member of USER_LEVEL_AGENTS.
PROJECT_AGENT = "my-custom-project-agent-xyz"


@pytest.fixture()
def temp_dirs():
    """Yield (fake_home, project_agents_dir, user_agents_dir)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        fake_home = base / "home"
        project_agents_dir = base / "project" / ".claude" / "agents"
        user_agents_dir = fake_home / ".claude" / "agents"
        project_agents_dir.mkdir(parents=True)
        user_agents_dir.mkdir(parents=True)
        yield fake_home, project_agents_dir, user_agents_dir


class TestGuardPredicates:
    """Basic predicate behavior."""

    def test_core_agent_recognized(self):
        assert is_user_level_agent(CORE_AGENT) is True
        # Title-case / .md variants normalize to the same CORE name.
        assert is_user_level_agent("Engineer.md") is True

    def test_project_agent_not_core(self):
        assert PROJECT_AGENT not in USER_LEVEL_AGENTS
        assert is_user_level_agent(PROJECT_AGENT) is False

    def test_user_level_dir_detection(self, temp_dirs):
        fake_home, project_agents_dir, user_agents_dir = temp_dirs
        with patch("pathlib.Path.home", return_value=fake_home):
            assert is_user_level_agents_dir(user_agents_dir) is True
            assert is_user_level_agents_dir(project_agents_dir) is False


class TestProjectLevelGuard:
    """skip_project_level_user_agent decision + self-heal behavior."""

    def test_core_agent_skipped_for_project_target(self, temp_dirs):
        """A CORE agent must be skipped when the target is project-level."""
        fake_home, project_agents_dir, _ = temp_dirs
        with patch("pathlib.Path.home", return_value=fake_home):
            assert skip_project_level_user_agent(CORE_AGENT, project_agents_dir) is True

    def test_project_agent_not_skipped(self, temp_dirs):
        """A non-CORE agent must NOT be skipped (it belongs at project level)."""
        fake_home, project_agents_dir, _ = temp_dirs
        with patch("pathlib.Path.home", return_value=fake_home):
            assert (
                skip_project_level_user_agent(PROJECT_AGENT, project_agents_dir)
                is False
            )

    def test_core_agent_allowed_for_user_level_target(self, temp_dirs):
        """Writing a CORE agent to the shared user-level dir is allowed."""
        fake_home, _, user_agents_dir = temp_dirs
        with patch("pathlib.Path.home", return_value=fake_home):
            assert skip_project_level_user_agent(CORE_AGENT, user_agents_dir) is False

    def test_stale_project_copy_is_pruned(self, temp_dirs):
        """A leftover project-level CORE agent file is removed on next deploy."""
        fake_home, project_agents_dir, _ = temp_dirs
        stale = project_agents_dir / f"{CORE_AGENT}.md"
        stale.write_text("---\nname: engineer\n---\n\n# stale duplicate\n")
        assert stale.exists()

        with patch("pathlib.Path.home", return_value=fake_home):
            skipped = skip_project_level_user_agent(CORE_AGENT, project_agents_dir)

        assert skipped is True
        assert not stale.exists(), "Stale project-level CORE agent must be pruned"

    def test_user_level_copy_never_touched(self, temp_dirs):
        """The shared ~/.claude/agents copy must never be removed by the guard."""
        fake_home, project_agents_dir, user_agents_dir = temp_dirs
        user_copy = user_agents_dir / f"{CORE_AGENT}.md"
        user_copy.write_text("---\nname: engineer\n---\n\n# user copy\n")

        with patch("pathlib.Path.home", return_value=fake_home):
            skip_project_level_user_agent(CORE_AGENT, project_agents_dir)

        assert user_copy.exists(), "User-level copy must be preserved"


class TestDeploymentPathsHonorGuard:
    """Every write path must skip CORE agents for project targets."""

    def _template(self, tmp_dir: Path, name: str) -> Path:
        template = tmp_dir / f"{name}.md"
        template.write_text(f"---\nname: {name}\nversion: 1.0.0\n---\n\n# {name}\n")
        return template

    def test_single_agent_deployer_skips_core_agent(self, temp_dirs):
        """SingleAgentDeployer.deploy_single_agent skips + prunes CORE agents."""
        from claude_mpm.services.agents.deployment.single_agent_deployer import (
            SingleAgentDeployer,
        )

        fake_home, project_agents_dir, _ = temp_dirs
        template_dir = project_agents_dir.parent
        template_file = self._template(template_dir, CORE_AGENT)

        # Seed a stale project-level duplicate to prove self-heal.
        stale = project_agents_dir / f"{CORE_AGENT}.md"
        stale.write_text("stale")

        deployer = SingleAgentDeployer(
            template_builder=None, version_manager=None, results_manager=None
        )
        results = {
            "deployed": [],
            "updated": [],
            "migrated": [],
            "skipped": [],
            "errors": [],
        }

        with patch("pathlib.Path.home", return_value=fake_home):
            deployer.deploy_single_agent(
                template_file=template_file,
                agents_dir=project_agents_dir,
                base_agent_data={},
                base_agent_version=(1, 0, 0),
                force_rebuild=True,
                deployment_mode="project",
                results=results,
            )

        assert CORE_AGENT in results["skipped"]
        assert not stale.exists(), "Stale project-level CORE agent must be pruned"
        assert not (project_agents_dir / f"{CORE_AGENT}.md").exists()

    def test_agent_processor_skips_core_agent(self, temp_dirs):
        """AgentProcessor.process_agent skips + prunes CORE agents."""
        from claude_mpm.services.agents.deployment.processors import (
            AgentDeploymentContext,
            AgentProcessor,
        )

        fake_home, project_agents_dir, _ = temp_dirs
        template_dir = project_agents_dir.parent
        template_file = self._template(template_dir, CORE_AGENT)

        stale = project_agents_dir / f"{CORE_AGENT}.md"
        stale.write_text("stale")

        context = AgentDeploymentContext.from_template_file(
            template_file=template_file,
            agents_dir=project_agents_dir,
            base_agent_data={},
            base_agent_version=(1, 0, 0),
            force_rebuild=True,
            deployment_mode="project",
            source_info="system",
        )
        processor = AgentProcessor(template_builder=None, version_manager=None)

        with patch("pathlib.Path.home", return_value=fake_home):
            result = processor.process_agent(context)

        assert result.status.value == "skipped"
        assert not stale.exists(), "Stale project-level CORE agent must be pruned"

    def test_project_agent_still_deploys_via_single_deployer(self, temp_dirs):
        """A non-CORE agent is still written to the project-level directory."""
        from claude_mpm.services.agents.deployment.processors import (
            AgentDeploymentContext,
            AgentProcessor,
        )

        fake_home, project_agents_dir, _ = temp_dirs
        template_dir = project_agents_dir.parent
        template_file = self._template(template_dir, PROJECT_AGENT)

        context = AgentDeploymentContext.from_template_file(
            template_file=template_file,
            agents_dir=project_agents_dir,
            base_agent_data={},
            base_agent_version=(1, 0, 0),
            force_rebuild=True,
            deployment_mode="project",
            source_info="project",
        )

        class _StubBuilder:
            def build_agent_markdown(self, *args, **kwargs):
                return "---\nname: my-custom-project-agent-xyz\n---\n\n# body\n"

        processor = AgentProcessor(
            template_builder=_StubBuilder(), version_manager=None
        )

        with patch("pathlib.Path.home", return_value=fake_home):
            result = processor.process_agent(context)

        assert result.status.value != "skipped"
        assert (project_agents_dir / f"{PROJECT_AGENT}.md").exists()
