"""Tests for the deprecated project-level deployment guard.

Fix A for issue #924 removed user-level agent routing.  All agents now deploy to
project-local ``.claude/agents/``.  :func:`skip_project_level_user_agent` is now
a no-op that always returns ``False`` and never prunes anything, and every
deployment path writes CORE (``USER_LEVEL_AGENTS``) agents into the project-level
directory just like any other agent.

The predicate helpers (:func:`is_user_level_agent`, :func:`is_user_level_agents_dir`)
are retained for migration/cleanup code and are still exercised here.
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
    """Basic predicate behavior (retained legacy helpers)."""

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


class TestDeprecatedGuardIsNoOp:
    """skip_project_level_user_agent() always returns False (Fix A for #924)."""

    def test_core_agent_not_skipped_for_project_target(self, temp_dirs):
        """A CORE agent is no longer skipped for a project-level target."""
        fake_home, project_agents_dir, _ = temp_dirs
        with patch("pathlib.Path.home", return_value=fake_home):
            assert (
                skip_project_level_user_agent(CORE_AGENT, project_agents_dir) is False
            )

    def test_project_agent_not_skipped(self, temp_dirs):
        """A non-CORE agent is not skipped either."""
        fake_home, project_agents_dir, _ = temp_dirs
        with patch("pathlib.Path.home", return_value=fake_home):
            assert (
                skip_project_level_user_agent(PROJECT_AGENT, project_agents_dir)
                is False
            )

    def test_core_agent_not_skipped_for_user_level_target(self, temp_dirs):
        """Always False, regardless of whether the target is the user-level dir."""
        fake_home, _, user_agents_dir = temp_dirs
        with patch("pathlib.Path.home", return_value=fake_home):
            assert skip_project_level_user_agent(CORE_AGENT, user_agents_dir) is False

    def test_stale_project_copy_is_not_pruned(self, temp_dirs):
        """The self-heal pruning was removed: a project-level file is left intact."""
        fake_home, project_agents_dir, _ = temp_dirs
        existing = project_agents_dir / f"{CORE_AGENT}.md"
        existing.write_text("---\nname: engineer\n---\n\n# project copy\n")
        assert existing.exists()

        with patch("pathlib.Path.home", return_value=fake_home):
            skipped = skip_project_level_user_agent(CORE_AGENT, project_agents_dir)

        assert skipped is False
        assert existing.exists(), "Guard must no longer prune project-level files"

    def test_user_level_copy_never_touched(self, temp_dirs):
        """The shared ~/.claude/agents copy must never be removed by the guard."""
        fake_home, project_agents_dir, user_agents_dir = temp_dirs
        user_copy = user_agents_dir / f"{CORE_AGENT}.md"
        user_copy.write_text("---\nname: engineer\n---\n\n# user copy\n")

        with patch("pathlib.Path.home", return_value=fake_home):
            skip_project_level_user_agent(CORE_AGENT, project_agents_dir)

        assert user_copy.exists(), "User-level copy must be preserved"


class TestDeploymentPathsDeployCoreAgents:
    """Every write path now deploys CORE agents to the project-level directory."""

    def _template(self, tmp_dir: Path, name: str) -> Path:
        template = tmp_dir / f"{name}.md"
        template.write_text(f"---\nname: {name}\nversion: 1.0.0\n---\n\n# {name}\n")
        return template

    def _deploy_via_processor(self, temp_dirs, agent_name: str):
        from claude_mpm.services.agents.deployment.processors import (
            AgentDeploymentContext,
            AgentProcessor,
        )

        fake_home, project_agents_dir, _ = temp_dirs
        template_dir = project_agents_dir.parent
        template_file = self._template(template_dir, agent_name)

        context = AgentDeploymentContext.from_template_file(
            template_file=template_file,
            agents_dir=project_agents_dir,
            base_agent_data={},
            base_agent_version=(1, 0, 0),
            force_rebuild=True,
            deployment_mode="project",
            source_info="system",
        )

        class _StubBuilder:
            def build_agent_markdown(self, *args, **kwargs):
                return f"---\nname: {agent_name}\n---\n\n# body\n"

        processor = AgentProcessor(
            template_builder=_StubBuilder(), version_manager=None
        )

        with patch("pathlib.Path.home", return_value=fake_home):
            result = processor.process_agent(context)
        return result, project_agents_dir

    def test_core_agent_deploys_to_project_level(self, temp_dirs):
        """A CORE agent is now written to project-level (not skipped)."""
        result, project_agents_dir = self._deploy_via_processor(temp_dirs, CORE_AGENT)

        assert result.status.value != "skipped"
        assert (project_agents_dir / f"{CORE_AGENT}.md").exists()

    def test_project_agent_still_deploys_via_processor(self, temp_dirs):
        """A non-CORE agent is still written to the project-level directory."""
        result, project_agents_dir = self._deploy_via_processor(
            temp_dirs, PROJECT_AGENT
        )

        assert result.status.value != "skipped"
        assert (project_agents_dir / f"{PROJECT_AGENT}.md").exists()
