"""Tests for agents_cleanup command - Phase 1 fixes for issue #299.

These tests verify:
1. Detection of underscore-named duplicates
2. Detection of -agent suffix duplicates
3. Content-identical file detection using SHA256 hashing
4. Proper selection of preferred duplicate (dash over underscore, shorter names)
"""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.cli.commands.agents_cleanup import (
    _find_agent_suffix_duplicates,
    _find_duplicate_agents_by_content,
    _find_old_underscore_agents,
    _get_file_hash,
    _normalize_agent_name,
    _select_preferred_duplicate,
    _strip_agent_suffix,
)


class TestNormalizeAgentName:
    """Tests for _normalize_agent_name helper function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("python_engineer.md", "pythonengineer"),
            ("python-engineer.md", "pythonengineer"),
            ("Python_Engineer.md", "pythonengineer"),
            ("PYTHON-ENGINEER.md", "pythonengineer"),
            ("research.md", "research"),
            ("research.json", "research"),
        ],
    )
    def test_normalize_agent_name(self, input_name: str, expected: str) -> None:
        """Test that agent names are normalized correctly for comparison."""
        result = _normalize_agent_name(input_name)
        assert result == expected


class TestStripAgentSuffix:
    """Tests for _strip_agent_suffix helper function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("research-agent", "research"),
            ("research_agent", "research"),
            ("python-engineer-agent", "python-engineer"),
            ("python_engineer_agent", "python_engineer"),
            ("research", "research"),  # No suffix
            ("research.md", "research"),  # With extension
            ("research-agent.md", "research"),
        ],
    )
    def test_strip_agent_suffix(self, input_name: str, expected: str) -> None:
        """Test that -agent and _agent suffixes are properly stripped."""
        result = _strip_agent_suffix(input_name)
        assert result == expected


class TestFindOldUnderscoreAgents:
    """Tests for _find_old_underscore_agents function."""

    def test_finds_underscore_agents_with_dash_equivalents(
        self, tmp_path: Path
    ) -> None:
        """Test that underscore-named agents with dash equivalents are detected."""
        # Create test files
        (tmp_path / "python_engineer.md").write_text("content")
        (tmp_path / "python-engineer.md").write_text("content")
        (tmp_path / "research.md").write_text("content")  # No underscore

        deployed = list(tmp_path.glob("*.md"))
        new_agents = ["python-engineer.md", "research.md"]

        old = _find_old_underscore_agents(deployed, new_agents)

        assert len(old) == 1
        assert old[0].name == "python_engineer.md"

    def test_no_false_positives_for_unique_underscore_names(
        self, tmp_path: Path
    ) -> None:
        """Test that underscore names without dash equivalents are not flagged."""
        # Create underscore-named file with no dash equivalent
        (tmp_path / "unique_special_agent.md").write_text("content")
        (tmp_path / "other-agent.md").write_text("content")

        deployed = list(tmp_path.glob("*.md"))
        new_agents = ["other-agent.md"]  # No equivalent for unique_special_agent

        old = _find_old_underscore_agents(deployed, new_agents)

        assert len(old) == 0


class TestFindAgentSuffixDuplicates:
    """Tests for _find_agent_suffix_duplicates function."""

    def test_finds_dash_agent_suffix_duplicates(self, tmp_path: Path) -> None:
        """Test that files with -agent suffix are detected when base exists."""
        # Create test files
        (tmp_path / "research.md").write_text("content")
        (tmp_path / "research-agent.md").write_text("content")  # Should be flagged

        deployed = list(tmp_path.glob("*.md"))
        new_agents = ["research.md"]

        duplicates = _find_agent_suffix_duplicates(deployed, new_agents)

        assert len(duplicates) == 1
        assert duplicates[0].name == "research-agent.md"

    def test_finds_underscore_agent_suffix_duplicates(self, tmp_path: Path) -> None:
        """Test that files with _agent suffix are detected when base exists."""
        # Create test files
        (tmp_path / "engineer.md").write_text("content")
        (tmp_path / "engineer_agent.md").write_text("content")  # Should be flagged

        deployed = list(tmp_path.glob("*.md"))
        new_agents = ["engineer.md"]

        duplicates = _find_agent_suffix_duplicates(deployed, new_agents)

        assert len(duplicates) == 1
        assert duplicates[0].name == "engineer_agent.md"

    def test_no_false_positives_for_standalone_agent_suffix(
        self, tmp_path: Path
    ) -> None:
        """Test that files ending in -agent without base are not flagged."""
        # Create only the -agent version (no base)
        (tmp_path / "special-agent.md").write_text("content")

        deployed = list(tmp_path.glob("*.md"))
        new_agents = []  # No corresponding base name in new agents

        duplicates = _find_agent_suffix_duplicates(deployed, new_agents)

        # special-agent.md should not be flagged because "special" doesn't exist
        assert len(duplicates) == 0


class TestFindDuplicateAgentsByContent:
    """Tests for _find_duplicate_agents_by_content function."""

    def test_finds_content_identical_files(self, tmp_path: Path) -> None:
        """Test that files with identical content are detected."""
        content = "identical content here"
        (tmp_path / "file1.md").write_text(content)
        (tmp_path / "file2.md").write_text(content)
        (tmp_path / "file3.md").write_text("different content")

        deployed = list(tmp_path.glob("*.md"))

        duplicates = _find_duplicate_agents_by_content(deployed)

        # Should have one hash with two files
        assert len(duplicates) == 1
        files = next(iter(duplicates.values()))
        assert len(files) == 2
        names = {f.name for f in files}
        assert names == {"file1.md", "file2.md"}

    def test_no_duplicates_for_unique_content(self, tmp_path: Path) -> None:
        """Test that unique files are not flagged as duplicates."""
        (tmp_path / "file1.md").write_text("content 1")
        (tmp_path / "file2.md").write_text("content 2")
        (tmp_path / "file3.md").write_text("content 3")

        deployed = list(tmp_path.glob("*.md"))

        duplicates = _find_duplicate_agents_by_content(deployed)

        # No duplicates expected
        assert len(duplicates) == 0


class TestSelectPreferredDuplicate:
    """Tests for _select_preferred_duplicate function."""

    def test_prefers_dash_over_underscore(self, tmp_path: Path) -> None:
        """Test that dash-named files are preferred over underscore-named."""
        content = "same content"
        underscore = tmp_path / "python_engineer.md"
        dash = tmp_path / "python-engineer.md"
        underscore.write_text(content)
        dash.write_text(content)

        keep, remove = _select_preferred_duplicate([underscore, dash])

        assert keep.name == "python-engineer.md"
        assert len(remove) == 1
        assert remove[0].name == "python_engineer.md"

    def test_prefers_shorter_names(self, tmp_path: Path) -> None:
        """Test that shorter names (without -agent suffix) are preferred."""
        content = "same content"
        short = tmp_path / "research.md"
        long = tmp_path / "research-agent.md"
        short.write_text(content)
        long.write_text(content)

        keep, remove = _select_preferred_duplicate([short, long])

        assert keep.name == "research.md"
        assert len(remove) == 1
        assert remove[0].name == "research-agent.md"

    def test_alphabetical_for_tie(self, tmp_path: Path) -> None:
        """Test that alphabetical order is used when other factors are equal."""
        content = "same content"
        aaa = tmp_path / "aaa.md"
        bbb = tmp_path / "bbb.md"
        aaa.write_text(content)
        bbb.write_text(content)

        keep, remove = _select_preferred_duplicate([bbb, aaa])  # Out of order

        assert keep.name == "aaa.md"
        assert len(remove) == 1
        assert remove[0].name == "bbb.md"


class TestGetFileHash:
    """Tests for _get_file_hash function."""

    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        """Test that identical content produces identical hashes."""
        content = "test content"
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"
        file1.write_text(content)
        file2.write_text(content)

        hash1 = _get_file_hash(file1)
        hash2 = _get_file_hash(file2)

        assert hash1 == hash2

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        """Test that different content produces different hashes."""
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"
        file1.write_text("content 1")
        file2.write_text("content 2")

        hash1 = _get_file_hash(file1)
        hash2 = _get_file_hash(file2)

        assert hash1 != hash2

    def test_hash_is_sha256_hex(self, tmp_path: Path) -> None:
        """Test that hash is a valid SHA256 hex string."""
        file = tmp_path / "test.md"
        file.write_text("test")

        file_hash = _get_file_hash(file)

        # SHA256 produces 64-character hex string
        assert len(file_hash) == 64
        assert all(c in "0123456789abcdef" for c in file_hash)
