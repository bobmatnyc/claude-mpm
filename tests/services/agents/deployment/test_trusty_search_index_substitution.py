"""Tests for per-project trusty-search index substitution in the deployer.

Regression coverage for GitHub issue #872:

PM_INSTRUCTIONS.md previously hardcoded the trusty-search index name as
``claude-mpm`` and that literal was composed VERBATIM into every project's
``PM_INSTRUCTIONS_DEPLOYED.md``. Agents in ANY project were therefore told to
search the ``claude-mpm`` index instead of their own.

The fix replaces the literal with a ``{{trusty_search_index}}`` placeholder in
the source PM_INSTRUCTIONS.md and resolves it per-project in
``SystemInstructionsDeployer`` with precedence:
  1. ``trusty_search.index_id`` from ``.claude-mpm/configuration.yaml`` if set;
  2. otherwise the working-directory basename;
  3. finally the ``"default"`` sentinel when neither yields a non-blank name.

These tests assert that:
  (a) an explicit config override is honoured;
  (b) the directory basename is used when no config is present;
  (c) the ``{{trusty_search_index}}`` placeholder never leaks into the output;
  (d) an empty/whitespace working-directory basename falls back to ``"default"``
      so the deployed file never renders an empty ``index:`` value.
"""

import logging
from pathlib import Path
from unittest.mock import PropertyMock, patch

from claude_mpm.config.paths import ClaudeMPMPaths
from claude_mpm.services.agents.deployment.system_instructions_deployer import (
    SystemInstructionsDeployer,
)


def _make_system_files(agents_path: Path) -> None:
    """Create minimal system-level framework files in *agents_path*.

    The system PM_INSTRUCTIONS.md contains the ``{{trusty_search_index}}``
    placeholder so the deployer has something to substitute, plus a
    ``## Identity`` marker so it passes the override/marker validation paths.
    """
    (agents_path / "PM_INSTRUCTIONS.md").write_text(
        "<!-- PM_INSTRUCTIONS_VERSION: 0016 -->\n"
        "# PM Instructions\n\n## Identity\n"
        "- **trusty-search**: `mcp__trusty-search__search` "
        "(index: {{trusty_search_index}})\n",
        encoding="utf-8",
    )
    (agents_path / "AGENT_DELEGATION.md").write_text(
        "# Agent Delegation\n\n## When to Delegate to Each Agent\nDelegation.\n",
        encoding="utf-8",
    )
    (agents_path / "WORKFLOW.md").write_text(
        "# Workflow\n\n## Mandatory 5-Phase Sequence\nPhases.\n",
        encoding="utf-8",
    )
    (agents_path / "MEMORY.md").write_text(
        "# Memory\n\n## Memory System\nMemory content.\n",
        encoding="utf-8",
    )


def _deploy(tmp_path: Path, working_directory: Path, agents_path: Path) -> str:
    """Run deploy_system_instructions and return the deployed file contents.

    A non-existent fake home guarantees no user-level override leaks in from the
    real ``~/.claude-mpm``, keeping the test isolated from the developer's CWD.
    """
    fake_home = tmp_path / "fakehome"  # non-existent → no user override

    logger = logging.getLogger("test_trusty_search_index_substitution")
    deployer = SystemInstructionsDeployer(logger, working_directory)
    results: dict = {"deployed": [], "updated": [], "errors": []}

    with (
        patch.object(
            ClaudeMPMPaths,
            "agents_dir",
            new_callable=PropertyMock,
            return_value=agents_path,
        ),
        patch(
            "claude_mpm.services.agents.deployment.system_instructions_deployer.Path.home",
            return_value=fake_home,
        ),
    ):
        deployer.deploy_system_instructions(
            target_dir=tmp_path,
            force_rebuild=True,
            results=results,
        )

    assert not results["errors"], f"Deployment errors: {results['errors']}"

    deployed_file = working_directory / ".claude-mpm" / "PM_INSTRUCTIONS_DEPLOYED.md"
    assert deployed_file.exists(), "PM_INSTRUCTIONS_DEPLOYED.md was not created"
    return deployed_file.read_text(encoding="utf-8")


class TestTrustySearchIndexSubstitution:
    """Per-project resolution of the {{trusty_search_index}} placeholder."""

    def test_config_index_id_override_is_used(self, tmp_path: Path) -> None:
        """``trusty_search.index_id`` from configuration.yaml wins."""
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "my-project"
        working_dir.mkdir()

        # Project configuration.yaml with an explicit index override.
        project_mpm_dir = working_dir / ".claude-mpm"
        project_mpm_dir.mkdir()
        (project_mpm_dir / "configuration.yaml").write_text(
            "trusty_search:\n  index_id: foo\n",
            encoding="utf-8",
        )

        _make_system_files(agents_path)
        deployed = _deploy(tmp_path, working_dir, agents_path)

        assert "index: foo" in deployed
        assert "{{trusty_search_index}}" not in deployed

    def test_directory_basename_fallback_when_no_config(self, tmp_path: Path) -> None:
        """With no config, the working-directory basename is used."""
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "some-other-repo"
        working_dir.mkdir()

        _make_system_files(agents_path)
        deployed = _deploy(tmp_path, working_dir, agents_path)

        assert "index: some-other-repo" in deployed
        # The historical hardcoded value must NOT appear when the dir differs.
        assert "index: claude-mpm" not in deployed
        assert "{{trusty_search_index}}" not in deployed

    def test_directory_basename_fallback_on_malformed_config(
        self, tmp_path: Path
    ) -> None:
        """A malformed configuration.yaml falls back to the basename, no crash."""
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "broken-config-repo"
        working_dir.mkdir()

        project_mpm_dir = working_dir / ".claude-mpm"
        project_mpm_dir.mkdir()
        (project_mpm_dir / "configuration.yaml").write_text(
            "trusty_search: [this, is, not, a, mapping\n",  # invalid YAML
            encoding="utf-8",
        )

        _make_system_files(agents_path)
        deployed = _deploy(tmp_path, working_dir, agents_path)

        assert "index: broken-config-repo" in deployed
        assert "{{trusty_search_index}}" not in deployed

    def test_placeholder_never_leaks(self, tmp_path: Path) -> None:
        """The raw placeholder must never survive into the deployed output."""
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "leak-check-repo"
        working_dir.mkdir()

        _make_system_files(agents_path)
        deployed = _deploy(tmp_path, working_dir, agents_path)

        assert "{{trusty_search_index}}" not in deployed


class TestResolveTrustySearchIndexUnit:
    """Direct unit coverage of the resolver helper."""

    def _deployer(self, working_directory: Path) -> SystemInstructionsDeployer:
        logger = logging.getLogger("test_resolve_trusty_search_index")
        return SystemInstructionsDeployer(logger, working_directory)

    def test_resolver_prefers_config_override(self, tmp_path: Path) -> None:
        working_dir = tmp_path / "proj"
        working_dir.mkdir()
        (working_dir / ".claude-mpm").mkdir(parents=True)
        (working_dir / ".claude-mpm" / "configuration.yaml").write_text(
            "trusty_search:\n  index_id: custom-index\n",
            encoding="utf-8",
        )
        assert (
            self._deployer(working_dir)._resolve_trusty_search_index() == "custom-index"
        )

    def test_resolver_falls_back_to_dir_name(self, tmp_path: Path) -> None:
        working_dir = tmp_path / "named-dir"
        working_dir.mkdir()
        assert self._deployer(working_dir)._resolve_trusty_search_index() == "named-dir"

    def test_resolver_ignores_blank_override(self, tmp_path: Path) -> None:
        working_dir = tmp_path / "blank-override-dir"
        (working_dir / ".claude-mpm").mkdir(parents=True)
        (working_dir / ".claude-mpm" / "configuration.yaml").write_text(
            'trusty_search:\n  index_id: "   "\n',
            encoding="utf-8",
        )
        assert (
            self._deployer(working_dir)._resolve_trusty_search_index()
            == "blank-override-dir"
        )

    def test_substitution_is_noop_without_placeholder(self, tmp_path: Path) -> None:
        working_dir = tmp_path / "noop-dir"
        working_dir.mkdir()
        text = "no placeholder here"
        assert self._deployer(working_dir)._apply_template_substitutions(text) == text

    def test_resolver_falls_back_to_default_for_empty_dir_name(self) -> None:
        """An empty working-directory basename (e.g. ``Path('/')``) resolves to
        the ``"default"`` sentinel rather than an empty string.

        Uses ``Path('/')`` directly: ``Path('/').name == ''``. No filesystem
        writes occur (the resolver only reads ``.name`` after the config lookup
        misses), so this stays isolated from the real root directory.
        """
        deployer = self._deployer(Path("/"))
        assert Path("/").name == ""  # guards the precondition this test relies on
        assert deployer._resolve_trusty_search_index() == "default"

    def test_substitution_renders_default_for_empty_dir_name(self) -> None:
        """End-to-end of the substitution: an empty basename must produce
        ``index: default`` in the output — never ``index: `` (empty value) and
        never a leaked ``{{trusty_search_index}}`` placeholder.
        """
        deployer = self._deployer(Path("/"))
        rendered = deployer._apply_template_substitutions(
            "- **trusty-search** (index: {{trusty_search_index}})\n"
        )
        assert "index: default" in rendered
        assert "{{trusty_search_index}}" not in rendered
        assert "index: )" not in rendered  # no empty value leaked
