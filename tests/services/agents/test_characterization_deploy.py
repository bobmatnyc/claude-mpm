"""CT-2: Characterization tests for GitSourceSyncService.deploy_agents_to_project().

These tests capture the CURRENT behavior of the Git-source deployment pipeline
as a safety net before refactoring. They document how deploy_agents_to_project()
discovers cached agents, deploys them to a project directory, and reports results.

Key behaviors captured:
- When agent_list is None, all cached agents are discovered and deployed
- Result dict contains "deployed", "updated", "skipped", "failed", "deployment_dir"
- Exclusion filtering is controlled by .claude-mpm/configuration.yaml
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.sources.git_source_sync_service import (
    GitSourceSyncService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(cache_dir: Path) -> GitSourceSyncService:
    """Create a GitSourceSyncService without triggering side effects.

    The real __init__ creates network sessions, SQLite state DBs, and
    registers sources.  We bypass all of that by using __new__ and setting
    only the attributes our tests exercise.
    """
    svc = object.__new__(GitSourceSyncService)
    svc.cache_dir = cache_dir
    svc.source_url = "https://example.com/agents"
    svc.source_id = "test-source"

    import logging

    svc.logger = logging.getLogger("test.git_source_sync")

    return svc


def _populate_nested_cache(cache_dir: Path, agent_names: list[str]) -> None:
    """Create agent .md files in a nested cache structure.

    Mimics the real cache layout:
        cache_dir/test-source/test-repo/agents/<category>/<name>.md
    """
    agents_dir = cache_dir / "test-source" / "test-repo" / "agents"
    for name in agent_names:
        category = name  # one agent per category for simplicity
        agent_file = agents_dir / category / f"{name}.md"
        agent_file.parent.mkdir(parents=True, exist_ok=True)
        agent_file.write_text(
            f"---\nname: {name.replace('-', ' ').title()}\n---\n# {name}\nContent.\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# CT-2 Tests
# ---------------------------------------------------------------------------


class TestCharacterizationDeployAgentsToProject:
    """CT-2: Characterize deploy_agents_to_project() current behavior."""

    def test_ct2_deploys_all_cached_agents_when_no_list(self, tmp_path):
        """When agent_list is None, _discover_cached_agents is called and all
        discovered agents are deployed to .claude/agents/."""
        cache_dir = tmp_path / "cache"
        _populate_nested_cache(cache_dir, ["engineer", "research", "qa"])

        svc = _make_service(cache_dir)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # We need to mock _discover_cached_agents because the nested cache
        # structure needs proper agent-path discovery
        discovered = ["engineer/engineer.md", "research/research.md", "qa/qa.md"]

        with patch.object(svc, "_discover_cached_agents", return_value=discovered):
            with patch.object(svc, "_resolve_cache_path") as mock_resolve:
                # Map each discovered path to the actual file in cache
                def resolve(agent_path):
                    name = Path(agent_path).stem
                    return (
                        cache_dir
                        / "test-source"
                        / "test-repo"
                        / "agents"
                        / name
                        / f"{name}.md"
                    )

                mock_resolve.side_effect = resolve

                result = svc.deploy_agents_to_project(project_dir, agent_list=None)

        # All three agents should appear in deployed or updated
        deployed_or_updated = result["deployed"] + result["updated"]
        assert len(deployed_or_updated) == 3

        # Verify files exist on disk
        deploy_dir = project_dir / ".claude" / "agents"
        assert deploy_dir.exists()
        deployed_files = list(deploy_dir.glob("*.md"))
        assert len(deployed_files) == 3

    def test_ct2_result_dict_has_expected_keys(self, tmp_path):
        """deploy_agents_to_project() returns a dict with all expected keys."""
        cache_dir = tmp_path / "cache"
        (cache_dir).mkdir(parents=True)

        svc = _make_service(cache_dir)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch.object(svc, "_discover_cached_agents", return_value=[]):
            result = svc.deploy_agents_to_project(project_dir, agent_list=None)

        expected_keys = {"deployed", "updated", "skipped", "failed", "deployment_dir"}
        assert expected_keys == set(result.keys())

        # All list values should be lists
        for key in ["deployed", "updated", "skipped", "failed"]:
            assert isinstance(result[key], list), f"{key} should be a list"

        # deployment_dir should be a string path
        assert isinstance(result["deployment_dir"], str)
        assert result["deployment_dir"].endswith(".claude/agents")

    def test_ct2_respects_no_config_file_no_exclusions(self, tmp_path):
        """When project has no .claude-mpm/configuration.yaml, no agents
        are excluded from deployment."""
        cache_dir = tmp_path / "cache"
        _populate_nested_cache(cache_dir, ["engineer", "ops"])

        svc = _make_service(cache_dir)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # Deliberately do NOT create .claude-mpm/configuration.yaml

        discovered = ["engineer/engineer.md", "ops/ops.md"]

        with patch.object(svc, "_discover_cached_agents", return_value=discovered):
            with patch.object(svc, "_resolve_cache_path") as mock_resolve:

                def resolve(agent_path):
                    name = Path(agent_path).stem
                    return (
                        cache_dir
                        / "test-source"
                        / "test-repo"
                        / "agents"
                        / name
                        / f"{name}.md"
                    )

                mock_resolve.side_effect = resolve

                result = svc.deploy_agents_to_project(project_dir, agent_list=None)

        # Both agents should be deployed (no exclusions applied)
        deployed_or_updated = result["deployed"] + result["updated"]
        assert len(deployed_or_updated) == 2
        assert result["failed"] == []

    def test_ct2_excludes_agents_from_configuration_yaml(self, tmp_path):
        """When .claude-mpm/configuration.yaml contains excluded_agents,
        those agents are filtered out of deployment even if they exist in cache.

        This captures the exclusion filtering behavior in
        deploy_agents_to_project() that reads excluded_agents from
        the project's configuration.yaml file.
        """
        import yaml

        cache_dir = tmp_path / "cache"
        _populate_nested_cache(cache_dir, ["engineer", "ops"])

        svc = _make_service(cache_dir)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create .claude-mpm/configuration.yaml with ops excluded
        config_dir = project_dir / ".claude-mpm"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "configuration.yaml"
        config_file.write_text(
            yaml.dump({"excluded_agents": ["ops"]}),
            encoding="utf-8",
        )

        discovered = ["engineer/engineer.md", "ops/ops.md"]

        # Mock Config to avoid singleton issues and return our test config
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: (
            ["ops"] if key == "excluded_agents" else default
        )

        with patch.object(svc, "_discover_cached_agents", return_value=discovered):
            with patch.object(svc, "_resolve_cache_path") as mock_resolve:

                def resolve(agent_path):
                    name = Path(agent_path).stem
                    return (
                        cache_dir
                        / "test-source"
                        / "test-repo"
                        / "agents"
                        / name
                        / f"{name}.md"
                    )

                mock_resolve.side_effect = resolve

                with patch("claude_mpm.core.config.Config", return_value=mock_config):
                    result = svc.deploy_agents_to_project(project_dir, agent_list=None)

        # engineer should be deployed
        deployed_or_updated = result["deployed"] + result["updated"]
        engineer_deployed = any("engineer" in name for name in deployed_or_updated)
        assert engineer_deployed, (
            f"engineer should be deployed but got: {deployed_or_updated}"
        )

        # ops should NOT be deployed (excluded)
        ops_deployed = any("ops" in name for name in deployed_or_updated)
        assert not ops_deployed, (
            f"ops should be excluded but was deployed: {deployed_or_updated}"
        )
