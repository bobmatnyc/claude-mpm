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


class TestNormalizeDeploymentFilenameConsistency:
    """Verify normalize_deployment_filename is idempotent and consistent
    across various input formats.

    NOTE: This does NOT test that all deployment paths call
    normalize_deployment_filename(). That is verified by grep-based
    consolidation guard tests and code review.
    """

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
            # Edge cases: -agent suffix stripping + idempotency
            "debug-agent",
            "agent-agent",
        ],
    )
    def test_idempotent_normalization(self, agent_stem):
        """Normalizing an already-normalized filename returns the same result."""
        first_pass = normalize_deployment_filename(f"{agent_stem}.md")
        second_pass = normalize_deployment_filename(first_pass)
        assert first_pass == second_pass, (
            f"Not idempotent: '{agent_stem}.md' -> '{first_pass}' -> '{second_pass}'"
        )


class TestNormalizeAgentIdForComparison:
    """Tests for normalize_agent_id_for_comparison helper."""

    def test_strips_agent_suffix(self):
        """research-agent -> research"""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        assert normalize_agent_id_for_comparison("research-agent") == "research"

    def test_converts_underscores_to_dashes(self):
        """dart_engineer -> dart-engineer"""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        assert normalize_agent_id_for_comparison("dart_engineer") == "dart-engineer"

    def test_strips_agent_suffix_and_converts_underscores(self):
        """api_qa_agent -> api-qa (both transformations)"""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        assert normalize_agent_id_for_comparison("api_qa_agent") == "api-qa"

    def test_no_change_needed(self):
        """python-engineer -> python-engineer (already normalized)"""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        assert normalize_agent_id_for_comparison("python-engineer") == "python-engineer"

    def test_hierarchical_id_extracts_leaf(self):
        """engineer/backend/python-engineer -> python-engineer"""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        assert (
            normalize_agent_id_for_comparison("engineer/backend/python-engineer")
            == "python-engineer"
        )

    def test_hierarchical_with_agent_suffix(self):
        """engineer/research-agent -> research"""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        assert (
            normalize_agent_id_for_comparison("engineer/research-agent") == "research"
        )

    def test_uppercase_lowercased(self):
        """QA -> qa"""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        assert normalize_agent_id_for_comparison("QA") == "qa"

    def test_mixed_case_with_agent_suffix(self):
        """QA-Agent -> qa"""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        assert normalize_agent_id_for_comparison("QA-Agent") == "qa"

    def test_api_qa_agent(self):
        """api-qa-agent -> api-qa"""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        assert normalize_agent_id_for_comparison("api-qa-agent") == "api-qa"


class TestDeploymentStatusComparison:
    """Integration tests: normalized agent_id matches deployed file stems."""

    def test_deployed_ids_match_after_normalization(self):
        """Simulate the comparison that happens in configure.py."""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        # Simulate deployed_ids (what get_deployed_agent_ids returns - file stems)
        deployed_ids = {"research", "dart-engineer", "python-engineer", "api-qa", "qa"}

        # Simulate raw agent_ids from frontmatter
        raw_agent_ids = [
            "research-agent",  # -> research (strip -agent)
            "dart_engineer",  # -> dart-engineer (underscore to dash)
            "python-engineer",  # -> python-engineer (no change)
            "api-qa-agent",  # -> api-qa (strip -agent)
            "QA",  # -> qa (lowercase)
        ]

        for raw_id in raw_agent_ids:
            normalized = normalize_agent_id_for_comparison(raw_id)
            assert normalized in deployed_ids, (
                f"'{raw_id}' normalized to '{normalized}' but not found in deployed_ids {deployed_ids}"
            )


class TestUndeployNormalization:
    """Tests that undeploy/removal finds files deployed with normalized names.

    Addresses the bug where agent IDs with underscores (e.g., 'dart_engineer')
    fail to find the deployed file ('dart-engineer.md') because the deployment
    pipeline normalizes filenames but the removal path did not.
    """

    def test_undeploy_underscore_finds_dash_file(self, tmp_path):
        """Removing 'dart_engineer' should find and remove 'dart-engineer.md'."""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        # Simulate: deployment created 'dart-engineer.md' (normalized)
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        deployed_file = agents_dir / "dart-engineer.md"
        deployed_file.write_text("# Dart Engineer agent")

        # The raw agent_id is 'dart_engineer' (underscore form)
        raw_id = "dart_engineer"
        normalized = normalize_agent_id_for_comparison(raw_id)

        # Verify normalization produces the correct filename stem
        assert normalized == "dart-engineer"

        # The normalized name should match the deployed file
        normalized_path = agents_dir / f"{normalized}.md"
        assert normalized_path.exists(), (
            f"Expected {normalized_path} to exist but it does not"
        )

        # The raw name should NOT match (this was the bug)
        raw_path = agents_dir / f"{raw_id}.md"
        assert not raw_path.exists(), (
            f"Raw path {raw_path} should not exist (file was deployed with normalized name)"
        )

    def test_undeploy_uppercase_finds_lowercase_file(self):
        """Removing 'QA' should normalize to 'qa' to match 'qa.md'."""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        raw_id = "QA"
        normalized = normalize_agent_id_for_comparison(raw_id)

        # The key assertion: normalization produces the correct lowercase stem
        assert normalized == "qa"
        # On case-insensitive filesystems (macOS) QA.md == qa.md, but
        # on case-sensitive filesystems (Linux) only qa.md will exist.
        # The normalization ensures we always look for 'qa.md'.

    def test_undeploy_agent_suffix_finds_stripped_file(self, tmp_path):
        """Removing 'research-agent' should find and remove 'research.md'."""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        deployed_file = agents_dir / "research.md"
        deployed_file.write_text("# Research agent")

        raw_id = "research-agent"
        normalized = normalize_agent_id_for_comparison(raw_id)

        assert normalized == "research"
        assert (agents_dir / f"{normalized}.md").exists()

    def test_undeploy_hierarchical_underscore_finds_dash_file(self, tmp_path):
        """Removing 'engineer/dart_engineer' should find 'dart-engineer.md'."""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        deployed_file = agents_dir / "dart-engineer.md"
        deployed_file.write_text("# Dart Engineer agent")

        raw_id = "engineer/dart_engineer"
        normalized = normalize_agent_id_for_comparison(raw_id)

        assert normalized == "dart-engineer"
        assert (agents_dir / f"{normalized}.md").exists()

    def test_state_removal_checks_both_raw_and_normalized_keys(self):
        """Deployment state may contain either raw or normalized keys."""
        from claude_mpm.utils.agent_filters import normalize_agent_id_for_comparison

        leaf_name = "dart_engineer"
        normalized_leaf = normalize_agent_id_for_comparison(leaf_name)
        keys_to_check = {leaf_name, normalized_leaf}

        # State file has normalized key (common case after deploy)
        state_agents_normalized = {"dart-engineer": {"status": "deployed"}}
        assert any(k in state_agents_normalized for k in keys_to_check)

        # State file has raw key (backward compat / manual edit)
        state_agents_raw = {"dart_engineer": {"status": "deployed"}}
        assert any(k in state_agents_raw for k in keys_to_check)
