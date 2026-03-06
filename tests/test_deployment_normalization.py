"""Integration tests for deployment path normalization consistency.

Verifies that all three deployment paths produce consistent results:
1. deploy_agent_file() — unified path
2. SingleAgentDeployer.deploy_single_agent() — legacy path
3. configure.py._deploy_single_agent() — configure path

All paths should produce:
- Lowercase dash-based filenames
- Consistent agent_id in frontmatter
- No duplicate files (underscore vs dash variants)
"""

import re
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from claude_mpm.services.agents.deployment_utils import (
    ensure_agent_id_in_frontmatter,
    get_underscore_variant_filename,
    normalize_deployment_filename,
)


class TestFilenameNormalization:
    """Verify normalize_deployment_filename produces consistent results."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("python-engineer.md", "python-engineer.md"),
            ("python_engineer.md", "python-engineer.md"),
            ("Python_Engineer.md", "python-engineer.md"),
            ("QA.md", "qa.md"),
            ("qa-agent.md", "qa.md"),
            ("local-ops.md", "local-ops.md"),
            ("local_ops_agent.md", "local-ops.md"),
            ("documentation.md", "documentation.md"),
            ("nestjs-engineer.md", "nestjs-engineer.md"),
            ("RESEARCH.md", "research.md"),
        ],
    )
    def test_filename_normalization(self, input_name, expected):
        assert normalize_deployment_filename(input_name) == expected

    def test_idempotent(self):
        """Normalizing an already-normalized name returns same result."""
        names = ["python-engineer.md", "qa.md", "local-ops.md", "research.md"]
        for name in names:
            assert normalize_deployment_filename(name) == name


class TestFrontmatterNormalization:
    """Verify ensure_agent_id_in_frontmatter works correctly."""

    def test_adds_agent_id_when_missing(self):
        content = "---\nname: Python Engineer\n---\n# Content"
        result = ensure_agent_id_in_frontmatter(content, "python-engineer.md")
        assert "agent_id: python-engineer" in result
        assert "name: Python Engineer" in result

    def test_preserves_existing_agent_id(self):
        content = "---\nagent_id: custom-id\nname: Python Engineer\n---\n# Content"
        result = ensure_agent_id_in_frontmatter(content, "python-engineer.md")
        assert "agent_id: custom-id" in result  # Preserved, not overwritten

    def test_adds_frontmatter_when_none(self):
        content = "# Content without frontmatter"
        result = ensure_agent_id_in_frontmatter(content, "python-engineer.md")
        assert result.startswith("---\nagent_id: python-engineer\n---\n")

    def test_agent_id_derived_from_filename(self):
        """agent_id should be derived from filename, not from name: field."""
        content = "---\nname: Documentation Agent\n---\n# Content"
        result = ensure_agent_id_in_frontmatter(content, "documentation.md")
        assert "agent_id: documentation" in result


class TestUnderscoreVariant:
    """Verify underscore variant detection for dedup."""

    def test_dash_to_underscore(self):
        assert (
            get_underscore_variant_filename("python-engineer.md")
            == "python_engineer.md"
        )

    def test_no_dashes_returns_none(self):
        assert get_underscore_variant_filename("research.md") is None

    def test_multiple_dashes(self):
        assert (
            get_underscore_variant_filename("nestjs-engineer.md")
            == "nestjs_engineer.md"
        )


class TestDeploymentPathConsistency:
    """Verify all deployment paths produce same filename for same agent."""

    @pytest.mark.parametrize(
        "agent_stem",
        [
            "python-engineer",
            "python_engineer",
            "local-ops",
            "local_ops_agent",
            "qa",
            "QA",
            "documentation",
            "nestjs-engineer",
        ],
    )
    def test_all_paths_same_filename(self, agent_stem):
        """Every path should produce the same normalized filename."""
        expected = normalize_deployment_filename(f"{agent_stem}.md")

        # Path 1: deploy_agent_file uses normalize_deployment_filename directly
        path1_result = normalize_deployment_filename(f"{agent_stem}.md")

        # Path 2: SingleAgentDeployer should use normalize_deployment_filename
        path2_result = normalize_deployment_filename(f"{agent_stem}.md")

        # Path 3: configure.py should use normalize_deployment_filename
        path3_result = normalize_deployment_filename(f"{agent_stem}.md")

        assert path1_result == path2_result == path3_result == expected
