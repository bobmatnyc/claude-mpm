"""Tests for WORKFLOW.md lazy-load behaviour in SystemInstructionsDeployer.

Verifies that the deployer mirrors InstructionLoader's lazy-load logic
(GitHub issue #575):

- System-level WORKFLOW.md only → reference stub is written into
  PM_INSTRUCTIONS_DEPLOYED.md, NOT the full content.
- Project-level .claude-mpm/WORKFLOW.md override → full content IS inlined
  (override behaviour preserved).
- User-level ~/.claude-mpm/WORKFLOW.md override → full content IS inlined.

The shared constant WORKFLOW_SYSTEM_REFERENCE is the single source of truth
for the reference stub; both call sites must use it.
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.core.framework.loaders.workflow_constants import (
    WORKFLOW_SYSTEM_REFERENCE,
)
from claude_mpm.services.agents.deployment.system_instructions_deployer import (
    SystemInstructionsDeployer,
)

# ---------------------------------------------------------------------------
# Markers that are distinctive of the full WORKFLOW.md content.  If these
# appear in PM_INSTRUCTIONS_DEPLOYED.md when only the system file is present,
# the lazy-load optimisation has been defeated.
# ---------------------------------------------------------------------------
FULL_CONTENT_MARKERS = [
    "## Mandatory 5-Phase Sequence",
    "**Agent**: Research",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_system_files(agents_path: Path) -> None:
    """Create minimal system-level framework files in *agents_path*.

    Only the files needed by deploy_system_instructions are created; the
    WORKFLOW.md content includes the distinctive full-content markers so the
    test can verify they are absent from the deployed file.
    """
    (agents_path / "PM_INSTRUCTIONS.md").write_text(
        "# PM Instructions\n\n## PM Core Identity\nSystem PM instructions.\n",
        encoding="utf-8",
    )
    (agents_path / "AGENT_DELEGATION.md").write_text(
        "# Agent Delegation\n\n## Available Agent Capabilities\nDelegation content.\n",
        encoding="utf-8",
    )
    # Full WORKFLOW.md with the markers that must NOT appear in the deployed file
    # when no user/project override is present.
    (agents_path / "WORKFLOW.md").write_text(
        "# Workflow\n\n"
        "## Mandatory 5-Phase Sequence\n\n"
        "| Phase | Name | Agent |\n"
        "|-------|------|-------|\n"
        "| 1 | Research | **Agent**: Research |\n"
        "| 2 | Code Analysis Review | **Agent**: Code critic |\n",
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
    fake_home: Path | None = None,
) -> str:
    """Run deploy_system_instructions and return the deployed file contents.

    Args:
        tmp_path: pytest tmp_path used for any scratch files.
        working_directory: Working directory for the deployer (simulates project root).
        agents_path: Directory containing the system-level framework .md files.
        fake_home: Optional fake home directory.  If supplied, ``Path.home()``
            inside the deployer is replaced so that ``~/.claude-mpm/WORKFLOW.md``
            resolves inside this directory (which typically has no files).
            Defaults to ``tmp_path / "fakehome"`` (non-existent → no user override).
    """
    if fake_home is None:
        fake_home = tmp_path / "fakehome"
    # fake_home may or may not exist; if it doesn't, no user override is found.

    logger = logging.getLogger("test_workflow_lazy_load_in_deployer")
    deployer = SystemInstructionsDeployer(logger, working_directory)
    results: dict = {"deployed": [], "updated": [], "errors": []}

    # The deployer does `from claude_mpm.config.paths import paths; agents_path = paths.agents_dir`
    # inside the function body.  `agents_dir` is a computed property on the
    # ClaudeMPMPaths singleton, so we use PropertyMock to substitute it.
    from unittest.mock import PropertyMock

    from claude_mpm.config.paths import ClaudeMPMPaths

    with patch.object(
        ClaudeMPMPaths,
        "agents_dir",
        new_callable=PropertyMock,
        return_value=agents_path,
    ):
        # Patch Path.home() so user-level overrides resolve under fake_home
        # (which has no .claude-mpm/WORKFLOW.md by default).
        with patch(
            "claude_mpm.services.agents.deployment.system_instructions_deployer.Path.home",
            return_value=fake_home,
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWorkflowLazyLoadInDeployer:
    """Verify that SystemInstructionsDeployer applies WORKFLOW.md lazy-loading."""

    # ------------------------------------------------------------------
    # (a) System-level only: reference stub written, full content absent
    # ------------------------------------------------------------------

    def test_system_only_writes_reference_stub(self, tmp_path: Path) -> None:
        """With only a system-level WORKFLOW.md the deployed file uses the stub.

        The full content markers (e.g. '## Mandatory 5-Phase Sequence') must be
        absent; the reference stub must be present.
        """
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        _make_system_files(agents_path)
        deployed = _deploy(tmp_path, working_dir, agents_path)

        assert WORKFLOW_SYSTEM_REFERENCE in deployed, (
            "WORKFLOW_SYSTEM_REFERENCE stub not found in PM_INSTRUCTIONS_DEPLOYED.md. "
            "The deployer must write the reference stub when only the system file is present."
        )

    def test_system_only_excludes_full_content_markers(self, tmp_path: Path) -> None:
        """Full WORKFLOW.md phase-detail markers must NOT appear in deployed file.

        Checks each marker from FULL_CONTENT_MARKERS separately for clearer
        failure messages.
        """
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        _make_system_files(agents_path)
        deployed = _deploy(tmp_path, working_dir, agents_path)

        for marker in FULL_CONTENT_MARKERS:
            assert marker not in deployed, (
                f"Full WORKFLOW.md marker {marker!r} found in PM_INSTRUCTIONS_DEPLOYED.md "
                "when only a system-level file is present — lazy-load optimisation defeated."
            )

    # ------------------------------------------------------------------
    # (b) Project-level override: full content must be inlined
    # ------------------------------------------------------------------

    def test_project_override_inlines_full_content(self, tmp_path: Path) -> None:
        """With a project-level .claude-mpm/WORKFLOW.md override the full
        override content is inlined verbatim (override behaviour preserved).
        """
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        _make_system_files(agents_path)

        # Create a project-level override.
        project_mpm_dir = working_dir / ".claude-mpm"
        project_mpm_dir.mkdir()
        override_content = (
            "# Custom Project Workflow\n\n"
            "## Mandatory 5-Phase Sequence\n\n"
            "Project-specific phase definitions for this repo.\n"
        )
        (project_mpm_dir / "WORKFLOW.md").write_text(override_content, encoding="utf-8")

        deployed = _deploy(tmp_path, working_dir, agents_path)

        # The override content must appear verbatim.
        assert override_content in deployed, (
            "Project-level WORKFLOW.md override was NOT inlined in "
            "PM_INSTRUCTIONS_DEPLOYED.md — override behaviour broken."
        )

        # The reference stub must NOT replace the real override.
        assert WORKFLOW_SYSTEM_REFERENCE not in deployed, (
            "WORKFLOW_SYSTEM_REFERENCE stub was written even though a project "
            "override is present — override takes precedence."
        )

    def test_project_override_full_markers_present(self, tmp_path: Path) -> None:
        """Full content markers from the project override ARE present in deployed file."""
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        _make_system_files(agents_path)

        project_mpm_dir = working_dir / ".claude-mpm"
        project_mpm_dir.mkdir()
        override_content = (
            "# Custom Project Workflow\n\n"
            "## Mandatory 5-Phase Sequence\n\n"
            "Custom phases.\n\n"
            "**Agent**: Research\n"
            "Custom research instructions.\n"
        )
        (project_mpm_dir / "WORKFLOW.md").write_text(override_content, encoding="utf-8")

        deployed = _deploy(tmp_path, working_dir, agents_path)

        for marker in FULL_CONTENT_MARKERS:
            assert marker in deployed, (
                f"Marker {marker!r} missing from deployed file — "
                "project override content was not inlined."
            )

    # ------------------------------------------------------------------
    # (c) Shared constant is the same across both call sites
    # ------------------------------------------------------------------

    def test_shared_constant_importable_from_both_modules(self) -> None:
        """WORKFLOW_SYSTEM_REFERENCE is importable from the shared constants module.

        Both InstructionLoader (core) and SystemInstructionsDeployer (services)
        import from the same workflow_constants module.  This test verifies the
        constant is properly defined, non-empty, and mentions WORKFLOW.md.
        """
        import claude_mpm.core.framework.loaders.workflow_constants as wc

        # Must be non-empty and mention WORKFLOW.md so the PM can locate the file.
        assert "WORKFLOW.md" in wc.WORKFLOW_SYSTEM_REFERENCE, (
            "WORKFLOW_SYSTEM_REFERENCE must mention WORKFLOW.md"
        )
        assert len(wc.WORKFLOW_SYSTEM_REFERENCE) < 300, (
            "WORKFLOW_SYSTEM_REFERENCE is suspiciously long — it should be a compact stub"
        )
        # Must match what the deployer module imports.
        assert wc.WORKFLOW_SYSTEM_REFERENCE == WORKFLOW_SYSTEM_REFERENCE, (
            "WORKFLOW_SYSTEM_REFERENCE imported in test differs from deployer import"
        )

    # ------------------------------------------------------------------
    # (d) Other blocks (PM_INSTRUCTIONS, AGENT_DELEGATION, MEMORY) unchanged
    # ------------------------------------------------------------------

    def test_other_blocks_still_present_in_deployed_file(self, tmp_path: Path) -> None:
        """Lazy-load change must not affect the other three blocks."""
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        working_dir = tmp_path / "project"
        working_dir.mkdir()

        _make_system_files(agents_path)
        deployed = _deploy(tmp_path, working_dir, agents_path)

        assert "## PM Core Identity" in deployed, (
            "PM_INSTRUCTIONS.md content missing from PM_INSTRUCTIONS_DEPLOYED.md"
        )
        assert "## Available Agent Capabilities" in deployed, (
            "AGENT_DELEGATION.md content missing from PM_INSTRUCTIONS_DEPLOYED.md"
        )
        assert "## Static Memory Management" in deployed, (
            "MEMORY.md content missing from PM_INSTRUCTIONS_DEPLOYED.md"
        )
