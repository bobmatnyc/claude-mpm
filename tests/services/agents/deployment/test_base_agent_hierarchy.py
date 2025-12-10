"""Tests for hierarchical BASE-AGENT.md template inheritance.

This test suite validates the hierarchical composition of agent templates
using BASE-AGENT.md files discovered in the directory tree.

Test Coverage:
- BASE-AGENT.md discovery walking up directory tree
- Template composition order (agent + local + parent + root)
- Composition with multiple nesting levels
- Graceful handling of missing BASE templates
- Repository root detection (.git directory)
- Legacy BASE_{TYPE}.md fallback
"""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.services.agents.deployment.agent_template_builder import (
    AgentTemplateBuilder,
)


@pytest.fixture
def template_builder():
    """Create AgentTemplateBuilder instance for testing."""
    return AgentTemplateBuilder()


@pytest.fixture
def temp_repo():
    """Create temporary directory structure for testing hierarchical BASE templates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # Create git root marker
        (repo_root / ".git").mkdir()

        yield repo_root


def create_base_template(path: Path, content: str):
    """Helper to create a BASE-AGENT.md file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def create_agent_template(path: Path, template_data: dict):
    """Helper to create an agent template Markdown file with YAML frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)

    # Extract instructions and create proper markdown format
    instructions = template_data.get("instructions", "")

    # Build YAML frontmatter with all required fields
    frontmatter_lines = ["---"]
    frontmatter_lines.append(f"name: {template_data.get('name', 'unnamed')}")
    frontmatter_lines.append(f"version: {template_data.get('version', '1.0.0')}")
    if "description" in template_data:
        frontmatter_lines.append(f"description: {template_data['description']}")
    if "agent_type" in template_data:
        frontmatter_lines.append(f"agent_type: {template_data['agent_type']}")
    frontmatter_lines.append("---")

    # Combine frontmatter and instructions
    content = "\n".join(frontmatter_lines) + "\n\n" + instructions
    path.write_text(content)


class TestBaseAgentDiscovery:
    """Test BASE-AGENT.md file discovery in directory hierarchy."""

    def test_discover_single_base_template(self, template_builder, temp_repo):
        """Test discovery of single BASE-AGENT.md in same directory."""
        # Create agent file and local BASE template
        agent_dir = temp_repo / "engineering"
        agent_dir.mkdir(parents=True)

        agent_file = agent_dir / "engineer.md"
        agent_file.write_text("# Engineer Agent")

        base_file = agent_dir / "BASE-AGENT.md"
        create_base_template(base_file, "# Engineering Base")

        # Discover BASE templates
        discovered = template_builder._discover_base_agent_templates(agent_file)

        assert len(discovered) == 1
        assert discovered[0] == base_file

    def test_discover_nested_base_templates(self, template_builder, temp_repo):
        """Test discovery of multiple BASE-AGENT.md files in hierarchy."""
        # Create directory structure
        # repo/
        #   BASE-AGENT.md           (root)
        #   engineering/
        #     BASE-AGENT.md         (parent)
        #     python/
        #       BASE-AGENT.md       (local)
        #       fastapi-engineer.md (agent)

        engineering_dir = temp_repo / "engineering"
        python_dir = engineering_dir / "python"
        python_dir.mkdir(parents=True)

        agent_file = python_dir / "fastapi-engineer.md"
        agent_file.write_text("# FastAPI Engineer")

        # Create BASE templates at each level
        local_base = python_dir / "BASE-AGENT.md"
        create_base_template(local_base, "# Python Base")

        parent_base = engineering_dir / "BASE-AGENT.md"
        create_base_template(parent_base, "# Engineering Base")

        root_base = temp_repo / "BASE-AGENT.md"
        create_base_template(root_base, "# Root Base")

        # Discover BASE templates
        discovered = template_builder._discover_base_agent_templates(agent_file)

        # Should discover all three in order: local, parent, root
        assert len(discovered) == 3
        assert discovered[0] == local_base
        assert discovered[1] == parent_base
        assert discovered[2] == root_base

    def test_discover_no_base_templates(self, template_builder, temp_repo):
        """Test discovery when no BASE-AGENT.md files exist."""
        agent_dir = temp_repo / "engineering"
        agent_dir.mkdir(parents=True)

        agent_file = agent_dir / "engineer.md"
        agent_file.write_text("# Engineer Agent")

        # Discover BASE templates (should be empty)
        discovered = template_builder._discover_base_agent_templates(agent_file)

        assert len(discovered) == 0

    def test_discover_partial_hierarchy(self, template_builder, temp_repo):
        """Test discovery with BASE templates at some but not all levels."""
        # Create structure with gaps
        # repo/
        #   BASE-AGENT.md           (root - EXISTS)
        #   engineering/
        #     (no BASE-AGENT.md)    (parent - MISSING)
        #     python/
        #       BASE-AGENT.md       (local - EXISTS)
        #       django-engineer.md  (agent)

        engineering_dir = temp_repo / "engineering"
        python_dir = engineering_dir / "python"
        python_dir.mkdir(parents=True)

        agent_file = python_dir / "django-engineer.md"
        agent_file.write_text("# Django Engineer")

        # Create BASE templates only at root and local (skip parent)
        local_base = python_dir / "BASE-AGENT.md"
        create_base_template(local_base, "# Python Base")

        root_base = temp_repo / "BASE-AGENT.md"
        create_base_template(root_base, "# Root Base")

        # Discover BASE templates
        discovered = template_builder._discover_base_agent_templates(agent_file)

        # Should discover two: local and root (parent is missing)
        assert len(discovered) == 2
        assert discovered[0] == local_base
        assert discovered[1] == root_base

    def test_stop_at_git_root(self, template_builder, temp_repo):
        """Test that discovery stops at .git directory."""
        # The temp_repo fixture already creates .git at root
        # Create nested structure
        deep_dir = temp_repo / "level1" / "level2" / "level3"
        deep_dir.mkdir(parents=True)

        agent_file = deep_dir / "agent.md"
        agent_file.write_text("# Deep Agent")

        root_base = temp_repo / "BASE-AGENT.md"
        create_base_template(root_base, "# Root Base")

        # Discover should find root and stop at .git
        discovered = template_builder._discover_base_agent_templates(agent_file)

        assert len(discovered) == 1
        assert discovered[0] == root_base

    def test_depth_limit(self, template_builder):
        """Test that discovery has depth limit to prevent infinite loops."""
        # Create very deep structure without .git marker
        with tempfile.TemporaryDirectory() as tmpdir:
            current = Path(tmpdir)

            # Create 15 nested levels (exceeds max_depth of 10)
            for i in range(15):
                current = current / f"level{i}"

            current.mkdir(parents=True)
            agent_file = current / "agent.md"
            agent_file.write_text("# Deep Agent")

            # Should not crash or loop infinitely
            discovered = template_builder._discover_base_agent_templates(agent_file)

            # May discover some, but won't crash
            assert isinstance(discovered, list)


class TestBaseAgentComposition:
    """Test hierarchical composition of agent templates with BASE-AGENT.md files."""

    def test_compose_with_single_base(self, template_builder, temp_repo):
        """Test composition with single local BASE-AGENT.md."""
        agent_dir = temp_repo / "engineering"
        agent_dir.mkdir(parents=True)

        # Create agent template
        agent_file = agent_dir / "engineer.md"
        template_data = {
            "name": "engineer",
            "description": "Software engineering agent",
            "agent_type": "engineer",
            "instructions": "# Engineer Instructions\n\nWrite quality code.",
        }
        create_agent_template(agent_file, template_data)

        # Create BASE template
        base_file = agent_dir / "BASE-AGENT.md"
        create_base_template(base_file, "# Engineering Principles\n\nFollow SOLID.")

        # Build agent markdown
        result = template_builder.build_agent_markdown(
            "engineer", agent_file, {}, "test"
        )

        # Verify composition order: agent instructions + BASE template
        assert "# Engineer Instructions" in result
        assert "Write quality code." in result
        assert "# Engineering Principles" in result
        assert "Follow SOLID." in result

        # Verify agent instructions come before BASE template
        agent_idx = result.index("# Engineer Instructions")
        base_idx = result.index("# Engineering Principles")
        assert agent_idx < base_idx

    def test_compose_with_nested_bases(self, template_builder, temp_repo):
        """Test composition with multiple nested BASE-AGENT.md files."""
        # Create structure
        # repo/
        #   BASE-AGENT.md           (root)
        #   engineering/
        #     BASE-AGENT.md         (parent)
        #     python/
        #       BASE-AGENT.md       (local)
        #       fastapi-engineer.md (agent)

        engineering_dir = temp_repo / "engineering"
        python_dir = engineering_dir / "python"
        python_dir.mkdir(parents=True)

        # Create agent template
        agent_file = python_dir / "fastapi-engineer.md"
        template_data = {
            "name": "fastapi-engineer",
            "description": "FastAPI specialist",
            "agent_type": "engineer",
            "instructions": "# FastAPI Instructions\n\nBuild async APIs.",
        }
        create_agent_template(agent_file, template_data)

        # Create BASE templates
        local_base = python_dir / "BASE-AGENT.md"
        create_base_template(local_base, "# Python Guidelines\n\nUse type hints.")

        parent_base = engineering_dir / "BASE-AGENT.md"
        create_base_template(parent_base, "# Engineering Standards\n\nWrite tests.")

        root_base = temp_repo / "BASE-AGENT.md"
        create_base_template(root_base, "# Company Values\n\nCustomer focus.")

        # Build agent markdown
        result = template_builder.build_agent_markdown(
            "fastapi-engineer", agent_file, {}, "test"
        )

        # Verify all parts are present
        assert "# FastAPI Instructions" in result
        assert "Build async APIs." in result
        assert "# Python Guidelines" in result
        assert "Use type hints." in result
        assert "# Engineering Standards" in result
        assert "Write tests." in result
        assert "# Company Values" in result
        assert "Customer focus." in result

        # Verify composition order: agent → local → parent → root
        fastapi_idx = result.index("# FastAPI Instructions")
        python_idx = result.index("# Python Guidelines")
        eng_idx = result.index("# Engineering Standards")
        root_idx = result.index("# Company Values")

        assert fastapi_idx < python_idx < eng_idx < root_idx

    def test_compose_without_base_templates(self, template_builder, temp_repo):
        """Test composition when no BASE-AGENT.md files exist."""
        agent_dir = temp_repo / "engineering"
        agent_dir.mkdir(parents=True)

        # Create agent template (no BASE templates)
        agent_file = agent_dir / "engineer.md"
        template_data = {
            "name": "engineer",
            "description": "Software engineering agent",
            "agent_type": "engineer",
            "instructions": "# Engineer Instructions\n\nWrite quality code.",
        }
        create_agent_template(agent_file, template_data)

        # Build agent markdown
        result = template_builder.build_agent_markdown(
            "engineer", agent_file, {}, "test"
        )

        # Should contain agent instructions but no BASE content
        assert "# Engineer Instructions" in result
        assert "Write quality code." in result
        # Should not crash or have empty sections

    def test_compose_with_empty_base_template(self, template_builder, temp_repo):
        """Test composition when BASE-AGENT.md exists but is empty."""
        agent_dir = temp_repo / "engineering"
        agent_dir.mkdir(parents=True)

        # Create agent template
        agent_file = agent_dir / "engineer.md"
        template_data = {
            "name": "engineer",
            "description": "Software engineering agent",
            "agent_type": "engineer",
            "instructions": "# Engineer Instructions\n\nWrite quality code.",
        }
        create_agent_template(agent_file, template_data)

        # Create empty BASE template
        base_file = agent_dir / "BASE-AGENT.md"
        create_base_template(base_file, "")

        # Build agent markdown
        result = template_builder.build_agent_markdown(
            "engineer", agent_file, {}, "test"
        )

        # Should contain agent instructions
        assert "# Engineer Instructions" in result
        assert "Write quality code." in result

    def test_separator_between_sections(self, template_builder, temp_repo):
        """Test that sections are separated with --- divider."""
        agent_dir = temp_repo / "engineering"
        agent_dir.mkdir(parents=True)

        # Create agent template
        agent_file = agent_dir / "engineer.md"
        template_data = {
            "name": "engineer",
            "description": "Software engineering agent",
            "agent_type": "engineer",
            "instructions": "# Agent Section",
        }
        create_agent_template(agent_file, template_data)

        # Create BASE template
        base_file = agent_dir / "BASE-AGENT.md"
        create_base_template(base_file, "# BASE Section")

        # Build agent markdown
        result = template_builder.build_agent_markdown(
            "engineer", agent_file, {}, "test"
        )

        # Verify separator exists between sections
        assert "---" in result
        assert "# Agent Section\n\n---\n\n# BASE Section" in result


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_malformed_base_template(self, template_builder, temp_repo):
        """Test handling of BASE-AGENT.md with encoding issues."""
        agent_dir = temp_repo / "engineering"
        agent_dir.mkdir(parents=True)

        # Create agent template
        agent_file = agent_dir / "engineer.md"
        template_data = {
            "name": "engineer",
            "description": "Software engineering agent",
            "agent_type": "engineer",
            "instructions": "# Engineer Instructions",
        }
        create_agent_template(agent_file, template_data)

        # Create BASE template that might have issues
        base_file = agent_dir / "BASE-AGENT.md"
        base_file.write_bytes(b"\xff\xfe# Invalid UTF-8")

        # Should not crash, may skip malformed template
        result = template_builder.build_agent_markdown(
            "engineer", agent_file, {}, "test"
        )

        # Should at minimum contain agent instructions
        assert "# Engineer Instructions" in result

    def test_symlink_handling(self, template_builder, temp_repo):
        """Test that symlinks to BASE-AGENT.md work correctly."""
        import os

        if not hasattr(os, "symlink"):
            pytest.skip("Symlinks not supported on this platform")

        agent_dir = temp_repo / "engineering"
        agent_dir.mkdir(parents=True)

        # Create agent template
        agent_file = agent_dir / "engineer.md"
        template_data = {
            "name": "engineer",
            "description": "Software engineering agent",
            "agent_type": "engineer",
            "instructions": "# Engineer Instructions",
        }
        create_agent_template(agent_file, template_data)

        # Create actual BASE template
        actual_base = temp_repo / "shared-base.md"
        create_base_template(actual_base, "# Shared Base Content")

        # Create symlink
        base_link = agent_dir / "BASE-AGENT.md"
        base_link.symlink_to(actual_base)

        # Build agent markdown
        result = template_builder.build_agent_markdown(
            "engineer", agent_file, {}, "test"
        )

        # Should resolve symlink and include content
        assert "# Shared Base Content" in result


class TestBackwardCompatibility:
    """Test backward compatibility with legacy BASE_{TYPE}.md pattern."""

    def test_fallback_to_legacy_base_type(self, template_builder, temp_repo):
        """Test fallback to BASE_{TYPE}.md when no BASE-AGENT.md exists."""
        # This test verifies that the legacy _load_base_agent_instructions
        # is still called as fallback when no hierarchical BASE templates found

        agent_dir = temp_repo / "engineering"
        agent_dir.mkdir(parents=True)

        # Create agent template with type
        agent_file = agent_dir / "engineer.md"
        template_data = {
            "name": "engineer",
            "description": "Software engineering agent",
            "agent_type": "engineer",
            "instructions": "# Engineer Instructions",
        }
        create_agent_template(agent_file, template_data)

        # No BASE-AGENT.md created - should trigger legacy fallback
        # Note: Legacy BASE_ENGINEER.md won't exist in temp dir either,
        # but the code path will be exercised

        # Build agent markdown
        result = template_builder.build_agent_markdown(
            "engineer", agent_file, {}, "test"
        )

        # Should complete without error (legacy fallback returns empty if not found)
        assert "# Engineer Instructions" in result

    def test_prefer_hierarchical_over_legacy(self, template_builder, temp_repo):
        """Test that hierarchical BASE-AGENT.md takes precedence over legacy."""
        agent_dir = temp_repo / "engineering"
        agent_dir.mkdir(parents=True)

        # Create agent template
        agent_file = agent_dir / "engineer.md"
        template_data = {
            "name": "engineer",
            "description": "Software engineering agent",
            "agent_type": "engineer",
            "instructions": "# Engineer Instructions",
        }
        create_agent_template(agent_file, template_data)

        # Create hierarchical BASE-AGENT.md
        base_file = agent_dir / "BASE-AGENT.md"
        create_base_template(base_file, "# Hierarchical Base")

        # If legacy BASE_ENGINEER.md existed, it should be ignored
        # Build agent markdown
        result = template_builder.build_agent_markdown(
            "engineer", agent_file, {}, "test"
        )

        # Should use hierarchical base, not legacy
        assert "# Hierarchical Base" in result
        # Should not have legacy marker (since we're using hierarchical)
        assert "Using legacy BASE_" not in result  # Not in content itself


class TestIntegration:
    """Integration tests with realistic agent repository structures."""

    def test_realistic_agent_repository(self, template_builder, temp_repo):
        """Test with realistic multi-tier agent repository structure."""
        # Create realistic structure
        # repo/
        #   BASE-AGENT.md                    (company-wide standards)
        #   engineering/
        #     BASE-AGENT.md                  (engineering principles)
        #     backend/
        #       BASE-AGENT.md                (backend best practices)
        #       python/
        #         BASE-AGENT.md              (Python guidelines)
        #         fastapi-engineer.md        (specific agent)

        # Create directory structure
        backend_dir = temp_repo / "engineering" / "backend"
        python_dir = backend_dir / "python"
        python_dir.mkdir(parents=True)

        # Create agent template
        agent_file = python_dir / "fastapi-engineer.md"
        template_data = {
            "name": "fastapi-engineer",
            "description": "FastAPI specialist",
            "agent_type": "engineer",
            "instructions": "# FastAPI Specialist\n\nExpert in FastAPI async APIs.",
        }
        create_agent_template(agent_file, template_data)

        # Create BASE templates at each level
        root_base = temp_repo / "BASE-AGENT.md"
        create_base_template(
            root_base, "# Company Standards\n\n- Customer first\n- Quality code"
        )

        eng_base = temp_repo / "engineering" / "BASE-AGENT.md"
        create_base_template(eng_base, "# Engineering Principles\n\n- SOLID\n- DRY")

        backend_base = backend_dir / "BASE-AGENT.md"
        create_base_template(
            backend_base, "# Backend Best Practices\n\n- API design\n- Database"
        )

        python_base = python_dir / "BASE-AGENT.md"
        create_base_template(
            python_base, "# Python Guidelines\n\n- Type hints\n- PEP 8"
        )

        # Build agent markdown
        result = template_builder.build_agent_markdown(
            "fastapi-engineer", agent_file, {}, "test"
        )

        # Verify all levels are composed
        assert "# FastAPI Specialist" in result
        assert "# Python Guidelines" in result
        assert "# Backend Best Practices" in result
        assert "# Engineering Principles" in result
        assert "# Company Standards" in result

        # Verify composition order (specific → general)
        indices = [
            result.index("# FastAPI Specialist"),
            result.index("# Python Guidelines"),
            result.index("# Backend Best Practices"),
            result.index("# Engineering Principles"),
            result.index("# Company Standards"),
        ]

        # Should be in increasing order (specific first, general last)
        assert indices == sorted(indices)
