"""Tests for deployment utilities.

Tests the filename normalization and frontmatter utilities used
to ensure consistent agent naming across deployment services.
(Issue #299 Phase 2)
"""

import pytest

from claude_mpm.services.agents.deployment_utils import (
    ensure_agent_id_in_frontmatter,
    get_underscore_variant_filename,
    normalize_deployment_filename,
)


class TestNormalizeDeploymentFilename:
    """Tests for normalize_deployment_filename function."""

    def test_already_dash_based(self):
        """Test that dash-based filenames are preserved."""
        assert (
            normalize_deployment_filename("python-engineer.md") == "python-engineer.md"
        )

    def test_underscore_to_dash(self):
        """Test that underscores are converted to dashes."""
        assert (
            normalize_deployment_filename("python_engineer.md") == "python-engineer.md"
        )

    def test_lowercase_conversion(self):
        """Test that filenames are lowercased."""
        assert (
            normalize_deployment_filename("Python-Engineer.md") == "python-engineer.md"
        )
        assert normalize_deployment_filename("QA.md") == "qa.md"

    def test_agent_suffix_stripped(self):
        """Test that -agent suffix is stripped for consistency."""
        assert normalize_deployment_filename("qa-agent.md") == "qa.md"
        assert normalize_deployment_filename("qa_agent.md") == "qa.md"

    def test_source_filename_precedence(self):
        """Test that source filename takes precedence over agent_id."""
        # Source filename is already normalized, agent_id is different
        result = normalize_deployment_filename("engineer.md", "python_engineer")
        assert result == "engineer.md"

    def test_complex_filenames(self):
        """Test handling of complex filenames."""
        assert (
            normalize_deployment_filename("data_science_engineer.md")
            == "data-science-engineer.md"
        )
        # -agent suffix is stripped for consistency
        assert normalize_deployment_filename("My-Custom-Agent.md") == "my-custom.md"

    def test_ensures_md_extension(self):
        """Test that .md extension is always present."""
        # The function expects .md extension in input, but ensure output has it
        assert normalize_deployment_filename("engineer.md").endswith(".md")


class TestEnsureAgentIdInFrontmatter:
    """Tests for ensure_agent_id_in_frontmatter function."""

    def test_no_frontmatter_adds_one(self):
        """Test that frontmatter is added if missing."""
        content = "# Python Engineer\n\nThis is an agent."
        result = ensure_agent_id_in_frontmatter(content, "python-engineer.md")

        assert result.startswith("---\nagent_id: python-engineer\n---\n")
        assert "# Python Engineer" in result

    def test_existing_frontmatter_without_agent_id(self):
        """Test that agent_id is added to existing frontmatter."""
        content = "---\nname: Python Engineer\nversion: 1.0\n---\n# Content"
        result = ensure_agent_id_in_frontmatter(content, "python-engineer.md")

        assert "agent_id: python-engineer" in result
        assert "name: Python Engineer" in result
        assert "version: 1.0" in result

    def test_existing_frontmatter_with_agent_id(self):
        """Test that existing agent_id is not overwritten."""
        content = "---\nagent_id: existing-id\nname: Python Engineer\n---\n# Content"
        result = ensure_agent_id_in_frontmatter(content, "python-engineer.md")

        # Should be unchanged
        assert result == content
        assert "agent_id: existing-id" in result

    def test_normalizes_filename_for_agent_id(self):
        """Test that derived agent_id is normalized."""
        content = "# Content"
        result = ensure_agent_id_in_frontmatter(content, "Python_Engineer.md")

        # Should lowercase and convert underscores
        assert "agent_id: python-engineer" in result

    def test_strips_agent_suffix_from_derived_id(self):
        """Test that -agent suffix is stripped when deriving agent_id."""
        content = "# QA Agent"
        result = ensure_agent_id_in_frontmatter(content, "qa-agent.md")

        assert "agent_id: qa" in result

    def test_malformed_frontmatter_unchanged(self):
        """Test that malformed frontmatter is handled gracefully."""
        # Missing closing ---
        content = "---\nname: Test\n# Content"
        result = ensure_agent_id_in_frontmatter(content, "test.md")

        # Should return unchanged due to malformed frontmatter
        assert result == content


class TestGetUnderscoreVariantFilename:
    """Tests for get_underscore_variant_filename function."""

    def test_dash_to_underscore(self):
        """Test that dashes are converted to underscores."""
        assert (
            get_underscore_variant_filename("python-engineer.md")
            == "python_engineer.md"
        )

    def test_multiple_dashes(self):
        """Test handling of multiple dashes."""
        assert (
            get_underscore_variant_filename("data-science-engineer.md")
            == "data_science_engineer.md"
        )

    def test_no_dashes_returns_none(self):
        """Test that files without dashes return None."""
        assert get_underscore_variant_filename("engineer.md") is None

    def test_preserves_extension(self):
        """Test that .md extension is preserved."""
        result = get_underscore_variant_filename("my-agent.md")
        assert result == "my_agent.md"
        assert result.endswith(".md")


class TestDeploymentUtilsIntegration:
    """Integration tests for deployment utilities working together."""

    def test_normalize_and_cleanup_cycle(self):
        """Test that normalize produces filenames that can be cleaned up."""
        # Simulate deployment cycle
        source_filename = "Python_Engineer.md"

        # Step 1: Normalize for deployment
        normalized = normalize_deployment_filename(source_filename)
        assert normalized == "python-engineer.md"

        # Step 2: Get underscore variant for cleanup
        underscore_variant = get_underscore_variant_filename(normalized)
        assert underscore_variant == "python_engineer.md"

        # The underscore variant would be cleaned up if it exists

    def test_frontmatter_with_normalized_filename(self):
        """Test that frontmatter agent_id matches normalized filename."""
        content = "# Test Agent"
        source_filename = "My_Test_Agent.md"

        # Step 1: Normalize filename (-agent suffix is stripped)
        normalized = normalize_deployment_filename(source_filename)
        assert normalized == "my-test.md"

        # Step 2: Ensure agent_id in frontmatter uses normalized name
        result = ensure_agent_id_in_frontmatter(content, normalized)
        assert "agent_id: my-test" in result

    def test_qa_agent_case(self):
        """Test the qa-agent vs qa naming case (real-world scenario)."""
        # Cache has "qa-agent.md", YAML might have agent_id: qa
        source_filename = "qa-agent.md"

        normalized = normalize_deployment_filename(source_filename)
        # Should strip -agent suffix
        assert normalized == "qa.md"

        # Frontmatter should use "qa" not "qa-agent"
        content = "# QA Agent"
        result = ensure_agent_id_in_frontmatter(content, normalized)
        assert "agent_id: qa" in result
