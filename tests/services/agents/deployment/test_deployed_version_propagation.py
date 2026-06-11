"""Tests for PM_INSTRUCTIONS_VERSION propagation in SystemInstructionsDeployer.

Regression coverage for GitHub issue #757:

PM_INSTRUCTIONS_DEPLOYED.md is the runtime fast-path (PRIORITY 1 in
InstructionLoader). The loader decides whether to use it by comparing the
``PM_INSTRUCTIONS_VERSION`` tag in the deployed file against the same tag in the
source PM_INSTRUCTIONS.md (via ``InstructionLoader._extract_version``). If the
deployed file lacks the tag, ``_extract_version`` returns 0, the loader sees
``0 < source`` and discards the freshly-rebuilt file as "stale" on every
startup — writing it, warning about it, and never using it.

The deployer must always propagate the *source* version tag into the written
file, independent of whether a user/project override of PM_INSTRUCTIONS.md
carries the tag (it usually does not).
"""

import logging
from pathlib import Path
from unittest.mock import PropertyMock, patch

from claude_mpm.config.paths import ClaudeMPMPaths
from claude_mpm.core.framework.loaders.instruction_loader import InstructionLoader
from claude_mpm.services.agents.deployment.system_instructions_deployer import (
    SystemInstructionsDeployer,
)

SOURCE_VERSION = 16  # arbitrary "source" framework version used in fixtures


def _make_system_files(agents_path: Path, *, version: int = SOURCE_VERSION) -> None:
    """Create minimal system-level framework files in *agents_path*.

    The system PM_INSTRUCTIONS.md carries a ``PM_INSTRUCTIONS_VERSION`` tag so
    the deployer has a source version to propagate.
    """
    (agents_path / "PM_INSTRUCTIONS.md").write_text(
        f"<!-- PM_INSTRUCTIONS_VERSION: {version:04d} -->\n"
        "# PM Instructions\n\n## PM Core Identity\nSystem PM instructions.\n",
        encoding="utf-8",
    )
    (agents_path / "AGENT_DELEGATION.md").write_text(
        "# Agent Delegation\n\n## Available Agent Capabilities\nDelegation content.\n",
        encoding="utf-8",
    )
    (agents_path / "WORKFLOW.md").write_text(
        "# Workflow\n\n## Mandatory 5-Phase Sequence\nPhases.\n",
        encoding="utf-8",
    )
    (agents_path / "MEMORY.md").write_text(
        "# Memory\n\n## Static Memory Management\nMemory content.\n",
        encoding="utf-8",
    )


def _deploy(
    tmp_path: Path,
    working_directory: Path,
    agents_path: Path,
) -> str:
    """Run deploy_system_instructions and return the deployed file contents."""
    fake_home = tmp_path / "fakehome"  # non-existent → no user override

    logger = logging.getLogger("test_deployed_version_propagation")
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


class TestDeployedVersionPropagation:
    """Deployed file carries the source version so the loader keeps it."""

    def test_deployed_version_matches_source_no_override(self, tmp_path: Path) -> None:
        """With only system files, the deployed file carries the source version."""
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        _make_system_files(agents_path)
        deployed = _deploy(tmp_path, working_dir, agents_path)

        loader = InstructionLoader()
        deployed_version = loader._extract_version(deployed)
        assert deployed_version == SOURCE_VERSION, (
            f"Deployed version {deployed_version} != source {SOURCE_VERSION}; "
            "InstructionLoader would discard the deployed file as stale."
        )

    def test_deployed_version_present_when_override_lacks_tag(
        self, tmp_path: Path
    ) -> None:
        """A project override without a version tag must NOT zero out the version.

        This is the exact issue #757 failure: a user customises
        .claude-mpm/PM_INSTRUCTIONS.md without copying the version comment, so
        the merged block has no tag. The deployer must still inject the source
        tag so the deployed file is not seen as v0.
        """
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        _make_system_files(agents_path)

        # Project override WITHOUT a version tag (the common customization case).
        project_mpm_dir = working_dir / ".claude-mpm"
        project_mpm_dir.mkdir()
        (project_mpm_dir / "PM_INSTRUCTIONS.md").write_text(
            "# Custom PM\n\n## Identity\nMy custom PM, no version tag.\n",
            encoding="utf-8",
        )

        deployed = _deploy(tmp_path, working_dir, agents_path)

        loader = InstructionLoader()
        deployed_version = loader._extract_version(deployed)
        assert deployed_version == SOURCE_VERSION, (
            "Override without a version tag caused the deployed file to read as "
            f"v{deployed_version:04d} instead of source v{SOURCE_VERSION:04d}; "
            "the file would be discarded as stale on every startup (issue #757)."
        )
        # And the override content is still present (override semantics intact).
        assert "My custom PM, no version tag." in deployed

    def test_deployed_not_stale_against_source(self, tmp_path: Path) -> None:
        """End-to-end: deployed version is never < source version.

        Mirrors the comparison InstructionLoader._load_filesystem_framework_instructions
        performs to decide between the deployed fast-path and the source file.
        """
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        _make_system_files(agents_path)
        deployed = _deploy(tmp_path, working_dir, agents_path)

        source_content = (agents_path / "PM_INSTRUCTIONS.md").read_text()
        loader = InstructionLoader()
        deployed_version = loader._extract_version(deployed)
        source_version = loader._extract_version(source_content)

        assert deployed_version >= source_version, (
            f"Deployed v{deployed_version:04d} < source v{source_version:04d}: "
            "the loader would log 'stale' and discard the fast-path."
        )

    def test_version_tag_appears_after_banner(self, tmp_path: Path) -> None:
        """The banner stays first; the version tag follows it.

        Banner-first is required (humans must see DO NOT EDIT immediately), and
        the version tag must still be discoverable by the unanchored regex.
        """
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        _make_system_files(agents_path)
        deployed = _deploy(tmp_path, working_dir, agents_path)

        assert deployed.startswith("<!-- AUTO-GENERATED by claude-mpm"), (
            "Banner must remain the first content in the deployed file."
        )
        assert "PM_INSTRUCTIONS_VERSION:" in deployed, (
            "Deployed file must contain a PM_INSTRUCTIONS_VERSION tag."
        )

    def test_missing_source_version_tag_is_tolerated(self, tmp_path: Path) -> None:
        """If the source itself has no version tag, deployment still succeeds.

        Both deployed and source read as v0, so deployed is not < source and the
        loader still accepts it — no crash, no spurious injection.
        """
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        # System PM_INSTRUCTIONS.md WITHOUT a version tag.
        (agents_path / "PM_INSTRUCTIONS.md").write_text(
            "# PM Instructions\n\n## PM Core Identity\nNo version.\n",
            encoding="utf-8",
        )
        (agents_path / "AGENT_DELEGATION.md").write_text(
            "# Agent Delegation\n\n## Available Agent Capabilities\nx\n",
            encoding="utf-8",
        )
        (agents_path / "WORKFLOW.md").write_text(
            "# Workflow\n\n## Mandatory 5-Phase Sequence\nx\n",
            encoding="utf-8",
        )
        (agents_path / "MEMORY.md").write_text(
            "# Memory\n\n## Static Memory Management\nx\n",
            encoding="utf-8",
        )

        deployed = _deploy(tmp_path, working_dir, agents_path)

        loader = InstructionLoader()
        # No tag anywhere → v0 == v0, deployed is not stale.
        assert loader._extract_version(deployed) == 0
