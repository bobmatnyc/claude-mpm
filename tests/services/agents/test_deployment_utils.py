"""Tests for deployment utilities.

Tests the filename normalization and frontmatter utilities used
to ensure consistent agent naming across deployment services.
(Issue #299 Phase 2 and Phase 3)
"""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.services.agents.deployment_utils import (
    DeploymentResult,
    ValidationResult,
    deploy_agent_file,
    ensure_agent_id_in_frontmatter,
    get_underscore_variant_filename,
    normalize_deployment_filename,
    validate_agent_file,
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


# ============================================================================
# Phase 3 Tests (Issue #299): Unified Deployment Interface
# ============================================================================


class TestValidateAgentFile:
    """Tests for validate_agent_file function (Phase 3)."""

    def test_valid_file_with_frontmatter(self, tmp_path):
        """Test validation of valid file with YAML frontmatter."""
        agent_file = tmp_path / "engineer.md"
        agent_file.write_text("---\nagent_id: engineer\nname: Engineer\n---\n# Content")

        result = validate_agent_file(agent_file)

        assert result.valid is True
        assert result.agent_id == "engineer"
        assert result.has_frontmatter is True
        assert len(result.errors) == 0

    def test_valid_file_without_frontmatter(self, tmp_path):
        """Test validation of valid file without frontmatter."""
        agent_file = tmp_path / "engineer.md"
        agent_file.write_text("# Engineer Agent\n\nThis is an engineer agent.")

        result = validate_agent_file(agent_file)

        assert result.valid is True
        assert result.agent_id == "engineer"  # Derived from filename
        assert result.has_frontmatter is False

    def test_nonexistent_file(self, tmp_path):
        """Test validation of non-existent file."""
        agent_file = tmp_path / "nonexistent.md"

        result = validate_agent_file(agent_file)

        assert result.valid is False
        assert "does not exist" in result.errors[0]

    def test_empty_file(self, tmp_path):
        """Test validation of empty file."""
        agent_file = tmp_path / "empty.md"
        agent_file.write_text("")

        result = validate_agent_file(agent_file)

        assert result.valid is False
        assert "empty" in result.errors[0].lower()

    def test_invalid_yaml_frontmatter(self, tmp_path):
        """Test validation of file with invalid YAML."""
        agent_file = tmp_path / "invalid.md"
        agent_file.write_text("---\n  invalid: yaml: here:\n---\n# Content")

        result = validate_agent_file(agent_file)

        assert result.valid is False
        assert any("YAML" in e for e in result.errors)

    def test_derives_agent_id_from_filename(self, tmp_path):
        """Test that agent_id is derived from filename when not in frontmatter."""
        agent_file = tmp_path / "python-engineer.md"
        agent_file.write_text("---\nname: Python Engineer\n---\n# Content")

        result = validate_agent_file(agent_file)

        assert result.valid is True
        assert result.agent_id == "python-engineer"


class TestDeployAgentFile:
    """Tests for deploy_agent_file function (Phase 3)."""

    def test_deploy_new_file(self, tmp_path):
        """Test deploying a new agent file."""
        # Setup
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        source_file = source_dir / "engineer.md"
        source_file.write_text("# Engineer\n\nAgent content.")

        # Deploy
        result = deploy_agent_file(source_file, deploy_dir)

        assert result.success is True
        assert result.action == "deployed"
        assert result.deployed_path == deploy_dir / "engineer.md"
        assert (deploy_dir / "engineer.md").exists()

    def test_deploy_adds_frontmatter(self, tmp_path):
        """Test that deployment adds agent_id to frontmatter."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        source_file = source_dir / "engineer.md"
        source_file.write_text("# Engineer\n\nAgent content.")

        result = deploy_agent_file(source_file, deploy_dir, ensure_frontmatter=True)

        assert result.success is True
        deployed_content = (deploy_dir / "engineer.md").read_text()
        assert "agent_id: engineer" in deployed_content

    def test_deploy_normalizes_filename(self, tmp_path):
        """Test that deployment normalizes underscore filenames to dashes."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        source_file = source_dir / "python_engineer.md"
        source_file.write_text("# Python Engineer")

        result = deploy_agent_file(source_file, deploy_dir)

        assert result.success is True
        # Should be normalized to dash-based
        assert result.deployed_path == deploy_dir / "python-engineer.md"
        assert (deploy_dir / "python-engineer.md").exists()

    def test_deploy_cleans_legacy_files(self, tmp_path):
        """Test that deployment cleans up underscore variant files."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        # Create legacy underscore file
        legacy_file = deploy_dir / "python_engineer.md"
        legacy_file.write_text("# Old content")

        source_file = source_dir / "python-engineer.md"
        source_file.write_text("# New content")

        result = deploy_agent_file(source_file, deploy_dir, cleanup_legacy=True)

        assert result.success is True
        assert "python_engineer.md" in result.cleaned_legacy
        assert not legacy_file.exists()
        assert (deploy_dir / "python-engineer.md").exists()

    def test_deploy_skips_unchanged(self, tmp_path):
        """Test that deployment skips files that haven't changed."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        content = "---\nagent_id: engineer\n---\n# Engineer"
        source_file = source_dir / "engineer.md"
        source_file.write_text(content)

        # First deployment
        result1 = deploy_agent_file(source_file, deploy_dir)
        assert result1.action == "deployed"

        # Second deployment (should skip)
        result2 = deploy_agent_file(source_file, deploy_dir)
        assert result2.action == "skipped"
        assert result2.success is True

    def test_deploy_force_updates(self, tmp_path):
        """Test that force=True always deploys."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        content = "---\nagent_id: engineer\n---\n# Engineer"
        source_file = source_dir / "engineer.md"
        source_file.write_text(content)

        # First deployment
        deploy_agent_file(source_file, deploy_dir)

        # Force deployment
        result = deploy_agent_file(source_file, deploy_dir, force=True)
        assert result.action == "updated"

    def test_deploy_nonexistent_source(self, tmp_path):
        """Test deployment of non-existent source file."""
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        source_file = tmp_path / "nonexistent.md"

        result = deploy_agent_file(source_file, deploy_dir)

        assert result.success is False
        assert "does not exist" in result.error

    def test_deploy_creates_directory(self, tmp_path):
        """Test that deployment creates target directory if missing."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        deploy_dir = tmp_path / "deploy" / "nested" / "agents"

        source_file = source_dir / "engineer.md"
        source_file.write_text("# Engineer")

        result = deploy_agent_file(source_file, deploy_dir)

        assert result.success is True
        assert deploy_dir.exists()


class TestDeploymentResultDataclass:
    """Tests for DeploymentResult dataclass."""

    def test_default_values(self):
        """Test default values of DeploymentResult."""
        result = DeploymentResult(success=False)

        assert result.success is False
        assert result.deployed_path is None
        assert result.action == "failed"
        assert result.error is None
        assert result.cleaned_legacy == []

    def test_success_result(self):
        """Test creating a success result."""
        result = DeploymentResult(
            success=True,
            deployed_path=Path("/test/engineer.md"),
            action="deployed",
        )

        assert result.success is True
        assert result.deployed_path == Path("/test/engineer.md")
        assert result.action == "deployed"


class TestValidationResultDataclass:
    """Tests for ValidationResult dataclass."""

    def test_default_values(self):
        """Test default values of ValidationResult."""
        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.agent_id is None
        assert result.has_frontmatter is False

    def test_invalid_result(self):
        """Test creating an invalid result."""
        result = ValidationResult(
            valid=False,
            errors=["File not found"],
            agent_id=None,
        )

        assert result.valid is False
        assert "File not found" in result.errors
