"""Tests for stale override detection in SystemInstructionsDeployer.

Verifies that the deployer detects and skips override files that contain
content from other blocks (indicating a stale previously-deployed merged file).
"""

import logging
import tempfile
from pathlib import Path

import pytest

from claude_mpm.services.agents.deployment.system_instructions_deployer import (
    BLOCK_MARKERS,
    SystemInstructionsDeployer,
)


@pytest.fixture
def deployer(tmp_path: Path) -> SystemInstructionsDeployer:
    """Create a SystemInstructionsDeployer with a temp working directory."""
    logger = logging.getLogger("test_stale_override")
    return SystemInstructionsDeployer(logger, tmp_path)


class TestDetectStaleOverride:
    """Tests for _detect_stale_override method."""

    def test_returns_true_when_pm_instructions_contains_workflow_marker(
        self, deployer: SystemInstructionsDeployer
    ) -> None:
        """PM_INSTRUCTIONS override containing WORKFLOW markers is stale."""
        stale_content = (
            "# PM Instructions\n\n"
            "Some custom content here.\n\n"
            "## Mandatory 5-Phase Sequence\n\n"
            "This belongs to WORKFLOW.md, not PM_INSTRUCTIONS.md."
        )
        assert (
            deployer._detect_stale_override("PM_INSTRUCTIONS.md", stale_content) is True
        )

    def test_returns_true_when_pm_instructions_contains_delegation_marker(
        self, deployer: SystemInstructionsDeployer
    ) -> None:
        """PM_INSTRUCTIONS override containing AGENT_DELEGATION markers is stale."""
        stale_content = (
            "# PM Instructions\n\n"
            "## Available Agent Capabilities\n\n"
            "This belongs to AGENT_DELEGATION.md."
        )
        assert (
            deployer._detect_stale_override("PM_INSTRUCTIONS.md", stale_content) is True
        )

    def test_returns_true_when_pm_instructions_contains_memory_marker(
        self, deployer: SystemInstructionsDeployer
    ) -> None:
        """PM_INSTRUCTIONS override containing MEMORY markers is stale."""
        stale_content = (
            "# PM Instructions\n\n"
            "## Static Memory Management\n\n"
            "This belongs to MEMORY.md."
        )
        assert (
            deployer._detect_stale_override("PM_INSTRUCTIONS.md", stale_content) is True
        )

    def test_returns_false_for_clean_override(
        self, deployer: SystemInstructionsDeployer
    ) -> None:
        """Clean override with only its own content is not stale."""
        clean_content = (
            "# Custom PM Instructions Override\n\n"
            "This is a legitimate project-specific override.\n"
            "It only contains PM-specific content.\n\n"
            "## PM Core Identity\n\n"
            "Custom identity definition."
        )
        assert (
            deployer._detect_stale_override("PM_INSTRUCTIONS.md", clean_content)
            is False
        )

    def test_returns_false_for_empty_content(
        self, deployer: SystemInstructionsDeployer
    ) -> None:
        """Empty override content is not stale."""
        assert deployer._detect_stale_override("PM_INSTRUCTIONS.md", "") is False

    def test_own_markers_do_not_trigger_stale_detection(
        self, deployer: SystemInstructionsDeployer
    ) -> None:
        """A block's own markers should not cause it to be flagged as stale."""
        # WORKFLOW.md containing its own marker is fine
        workflow_content = (
            "# Custom Workflow Override\n\n"
            "## Mandatory 5-Phase Sequence\n\n"
            "Custom phase definitions."
        )
        assert deployer._detect_stale_override("WORKFLOW.md", workflow_content) is False

    def test_all_blocks_have_markers(self) -> None:
        """Every block in BLOCK_MARKERS has at least one marker defined."""
        expected_blocks = [
            "PM_INSTRUCTIONS.md",
            "AGENT_DELEGATION.md",
            "WORKFLOW.md",
            "MEMORY.md",
        ]
        for block in expected_blocks:
            assert block in BLOCK_MARKERS, f"Missing markers for {block}"
            assert len(BLOCK_MARKERS[block]) > 0, f"No markers defined for {block}"


class TestResolveBlockWithStaleDetection:
    """Tests that _resolve_block skips stale overrides and falls back to system default."""

    def test_skips_stale_project_override_uses_system_default(
        self, deployer: SystemInstructionsDeployer, tmp_path: Path
    ) -> None:
        """When project override is stale, system default should be used instead."""
        # Set up system default
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        system_file = agents_path / "PM_INSTRUCTIONS.md"
        system_content = "# System Default PM Instructions"
        system_file.write_text(system_content)

        # Set up stale project override (contains WORKFLOW marker)
        project_override_dir = tmp_path / ".claude-mpm"
        project_override_dir.mkdir()
        stale_override = project_override_dir / "PM_INSTRUCTIONS.md"
        stale_override.write_text(
            "# Stale merged file\n\n"
            "## PM Core Identity\n\n"
            "PM content here.\n\n"
            "## Mandatory 5-Phase Sequence\n\n"
            "This is WORKFLOW content that should not be here."
        )

        result = deployer._resolve_block("PM_INSTRUCTIONS.md", agents_path)
        assert result == system_content

    def test_uses_clean_project_override(
        self, deployer: SystemInstructionsDeployer, tmp_path: Path
    ) -> None:
        """When project override is clean, it should be used instead of system default."""
        # Set up system default
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        system_file = agents_path / "PM_INSTRUCTIONS.md"
        system_file.write_text("# System Default")

        # Set up clean project override
        project_override_dir = tmp_path / ".claude-mpm"
        project_override_dir.mkdir()
        clean_override = project_override_dir / "PM_INSTRUCTIONS.md"
        override_content = "# Custom Project PM Instructions\n\nLegitimate override."
        clean_override.write_text(override_content)

        result = deployer._resolve_block("PM_INSTRUCTIONS.md", agents_path)
        assert result == override_content

    def test_stale_override_logs_warning(
        self,
        deployer: SystemInstructionsDeployer,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Stale override detection should log a warning."""
        # Set up system default
        agents_path = tmp_path / "agents"
        agents_path.mkdir()
        system_file = agents_path / "PM_INSTRUCTIONS.md"
        system_file.write_text("# System Default")

        # Set up stale project override
        project_override_dir = tmp_path / ".claude-mpm"
        project_override_dir.mkdir()
        stale_override = project_override_dir / "PM_INSTRUCTIONS.md"
        stale_override.write_text(
            "# Stale\n\n## Available Agent Capabilities\n\nFrom AGENT_DELEGATION."
        )

        with caplog.at_level(logging.WARNING):
            deployer._resolve_block("PM_INSTRUCTIONS.md", agents_path)

        assert "Stale override detected" in caplog.text
        assert "PM_INSTRUCTIONS.md" in caplog.text
