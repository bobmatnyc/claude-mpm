"""Test memory aggregation functionality."""

from pathlib import Path

import pytest

from claude_mpm.core.framework_loader import FrameworkLoader


class TestMemoryAggregation:
    """Test the _aggregate_memories method."""

    def test_single_memory_entry():
        """Test that a single memory entry is returned as-is."""
        loader = FrameworkLoader()
        entries = [
            {
                "source": "user",
                "content": "- Memory item 1\n- Memory item 2",
                "path": Path("/fake/path"),
            }
        ]
        result = loader._aggregate_memories(entries)
        assert result == "- Memory item 1\n- Memory item 2"

    def test_unsectioned_bullet_points_only():
        """Test aggregation of simple bullet-point memories without sections."""
        loader = FrameworkLoader()
        entries = [
            {
                "source": "user",
                "content": "- User memory 1\n- User memory 2\n- Shared memory",
                "path": Path("/fake/user"),
            },
            {
                "source": "project",
                "content": "- Project memory 1\n- Project memory 2\n- Shared memory",
                "path": Path("/fake/project"),
            },
        ]
        result = loader._aggregate_memories(entries)

        # Should have aggregated header
        assert "# Aggregated Memory" in result
        assert "*This memory combines user-level and project-level memories.*" in result

        # Should include all unique memories
        assert "- User memory 1" in result
        assert "- User memory 2" in result
        assert "- Project memory 1" in result
        assert "- Project memory 2" in result

        # Shared memory should appear only once (project overrides user)
        assert result.count("- Shared memory") == 1

    def test_sectioned_memories():
        """Test aggregation of memories with section headers."""
        loader = FrameworkLoader()
        entries = [
            {
                "source": "user",
                "content": "## Section A\n- Item A1\n- Item A2\n\n## Section B\n- Item B1",
                "path": Path("/fake/user"),
            },
            {
                "source": "project",
                "content": "## Section A\n- Item A3\n- Item A2\n\n## Section C\n- Item C1",
                "path": Path("/fake/project"),
            },
        ]
        result = loader._aggregate_memories(entries)

        # Should have sections
        assert "## Section A" in result
        assert "## Section B" in result
        assert "## Section C" in result

        # Items should be under correct sections
        lines = result.split("\n")
        section_a_idx = lines.index("## Section A")
        section_b_idx = lines.index("## Section B")
        lines.index("## Section C")

        # Section A should have all unique items
        section_a_content = "\n".join(lines[section_a_idx:section_b_idx])
        assert "- Item A1" in section_a_content
        assert "- Item A2" in section_a_content
        assert "- Item A3" in section_a_content

    def test_mixed_sectioned_and_unsectioned():
        """Test aggregation of memories with both sections and orphaned bullets."""
        loader = FrameworkLoader()
        entries = [
            {
                "source": "user",
                "content": "- Orphaned bullet 1\n- Orphaned bullet 2\n\n## Section A\n- Section item 1",
                "path": Path("/fake/user"),
            },
            {
                "source": "project",
                "content": "- Orphaned bullet 3\n\n## Section A\n- Section item 2\n\n## Section B\n- Item B1",
                "path": Path("/fake/project"),
            },
        ]
        result = loader._aggregate_memories(entries)

        # Should have both orphaned bullets and sections
        assert "- Orphaned bullet 1" in result
        assert "- Orphaned bullet 2" in result
        assert "- Orphaned bullet 3" in result
        assert "## Section A" in result
        assert "## Section B" in result

        # Orphaned bullets should appear before sections
        lines = result.split("\n")

        # Find indices
        orphan_indices = []
        section_indices = []
        for i, line in enumerate(lines):
            if line.startswith("- Orphaned"):
                orphan_indices.append(i)
            elif line.startswith("## Section"):
                section_indices.append(i)

        # All orphaned bullets should come before all sections
        if orphan_indices and section_indices:
            assert max(orphan_indices) < min(section_indices)

    def test_metadata_preservation():
        """Test that metadata HTML comments are preserved."""
        loader = FrameworkLoader()
        entries = [
            {
                "source": "user",
                "content": "<!-- METADATA: user -->\n- User memory",
                "path": Path("/fake/user"),
            },
            {
                "source": "project",
                "content": "<!-- METADATA: project -->\n- Project memory",
                "path": Path("/fake/project"),
            },
        ]
        result = loader._aggregate_memories(entries)

        # Both metadata should be preserved
        assert "<!-- METADATA: user -->" in result
        assert "<!-- METADATA: project -->" in result

        # Metadata should appear at the top
        lines = result.split("\n")
        metadata_lines = [l for l in lines if l.startswith("<!-- ")]
        assert len(metadata_lines) == 2
        assert lines.index(metadata_lines[0]) < lines.index("# Aggregated Memory")

    def test_project_overrides_user():
        """Test that project-level memories override user-level for duplicates."""
        loader = FrameworkLoader()
        entries = [
            {
                "source": "user",
                "content": "- Shared memory item\n- User only item",
                "path": Path("/fake/user"),
            },
            {
                "source": "project",
                "content": "- Shared memory item\n- Project only item",
                "path": Path("/fake/project"),
            },
        ]
        result = loader._aggregate_memories(entries)

        # Shared item should appear only once
        assert result.count("- Shared memory item") == 1

        # Both unique items should be present
        assert "- User only item" in result
        assert "- Project only item" in result

    def test_empty_memories():
        """Test handling of empty memory entries."""
        loader = FrameworkLoader()

        # Test empty list
        assert loader._aggregate_memories([]) == ""

        # Test entries with empty content
        entries = [
            {"source": "user", "content": "", "path": Path("/fake/user")},
            {
                "source": "project",
                "content": "- Valid memory",
                "path": Path("/fake/project"),
            },
        ]
        result = loader._aggregate_memories(entries)
        assert "- Valid memory" in result

    def test_non_bullet_unsectioned_content():
        """Test that non-bullet unsectioned content is handled properly."""
        loader = FrameworkLoader()
        entries = [
            {
                "source": "user",
                "content": "Random text line\n- Bullet point\nAnother random line\n## Section\n- Section item",
                "path": Path("/fake/user"),
            }
        ]
        result = loader._aggregate_memories(entries)

        # Non-header orphaned content should be included
        assert "Random text line" in result
        assert "Another random line" in result
        assert "- Bullet point" in result
        assert "## Section" in result
        assert "- Section item" in result

    def test_headers_without_sections_ignored():
        """Test that header lines without section designation are not treated as content."""
        loader = FrameworkLoader()

        # Test with single entry - should return as-is
        entries = [
            {
                "source": "user",
                "content": "# Main Header\n- Bullet point 1\n### Sub Header\n- Bullet point 2",
                "path": Path("/fake/user"),
            }
        ]
        result = loader._aggregate_memories(entries)

        # Single entry returns as-is
        assert (
            result
            == "# Main Header\n- Bullet point 1\n### Sub Header\n- Bullet point 2"
        )

        # Test with multiple entries - headers should be filtered
        entries = [
            {
                "source": "user",
                "content": "# Main Header\n- Bullet point 1\n### Sub Header\n- Bullet point 2",
                "path": Path("/fake/user"),
            },
            {
                "source": "project",
                "content": "- Bullet point 3",
                "path": Path("/fake/project"),
            },
        ]
        result = loader._aggregate_memories(entries)

        # In aggregated output, non-section headers should not be included
        lines = result.split("\n")
        content_after_header = "\n".join(lines[4:])  # Skip the aggregation header

        # Headers should not be in the aggregated content part
        assert "# Main Header" not in content_after_header
        assert "### Sub Header" not in content_after_header

        # Bullet points should be included
        assert "- Bullet point 1" in result
        assert "- Bullet point 2" in result
        assert "- Bullet point 3" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
