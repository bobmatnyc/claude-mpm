"""
Test ProjectKnowledgeExtractor functionality.

Quick test to verify knowledge extraction from git, logs, and memory files.
"""

import tempfile
from pathlib import Path

from claude_mpm.cli.commands.mpm_init.knowledge_extractor import (
    ProjectKnowledgeExtractor,
)


def test_knowledge_extractor_initialization():
    """Test basic initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        extractor = ProjectKnowledgeExtractor(project_path)

        assert extractor.project_path == project_path
        assert extractor.claude_mpm_dir == project_path / ".claude-mpm"
        assert extractor.is_git_repo is False


def test_extract_from_git_no_repo():
    """Test git extraction when not a git repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        extractor = ProjectKnowledgeExtractor(project_path)

        insights = extractor.extract_from_git(days=90)

        assert insights["available"] is False
        assert "message" in insights


def test_extract_from_logs_no_directory():
    """Test log extraction when .claude-mpm/responses doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        extractor = ProjectKnowledgeExtractor(project_path)

        insights = extractor.extract_from_logs()

        assert insights["available"] is False


def test_extract_from_memory_no_directory():
    """Test memory extraction when .claude-mpm/memories doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        extractor = ProjectKnowledgeExtractor(project_path)

        insights = extractor.extract_from_memory()

        assert insights["available"] is False


def test_extract_all():
    """Test extract_all method combines all sources."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        extractor = ProjectKnowledgeExtractor(project_path)

        all_insights = extractor.extract_all(days=90)

        assert "git_insights" in all_insights
        assert "log_insights" in all_insights
        assert "memory_insights" in all_insights


def test_parse_memory_sections():
    """Test markdown section parsing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        extractor = ProjectKnowledgeExtractor(project_path)

        content = """# Memory File

## Project Architecture
- Service-oriented architecture
- Repository pattern

## Implementation Guidelines
- Use type hints
- Write tests first

## Common Mistakes to Avoid
- Don't use global state
- Avoid mutable defaults
"""

        sections = extractor._parse_memory_sections(content)

        assert "Project Architecture" in sections
        assert "Implementation Guidelines" in sections
        assert "Common Mistakes to Avoid" in sections


def test_extract_memory_items():
    """Test extracting items from memory section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        extractor = ProjectKnowledgeExtractor(project_path)

        section_content = """
- Service-oriented architecture
- Repository pattern
- Event-driven design
"""

        items = extractor._extract_memory_items(section_content, "engineer")

        assert len(items) == 3
        assert all(item.startswith("[engineer]") for item in items)


if __name__ == "__main__":
    # Run basic tests
    test_knowledge_extractor_initialization()
    test_extract_from_git_no_repo()
    test_extract_from_logs_no_directory()
    test_extract_from_memory_no_directory()
    test_extract_all()
    test_parse_memory_sections()
    test_extract_memory_items()

    print("✓ All tests passed!")
