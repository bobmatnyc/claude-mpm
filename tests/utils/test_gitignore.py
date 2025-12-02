"""Tests for gitignore management utilities.

Test Coverage:
- GitIgnoreManager class methods
- File creation scenarios (new file, existing file)
- Duplicate detection and prevention
- Edge cases (empty files, missing newlines, binary files)
- Error handling (permissions, missing directories)
- High-level ensure_claude_mpm_gitignore() function
"""

from pathlib import Path

import pytest

from claude_mpm.utils.gitignore import GitIgnoreManager, ensure_claude_mpm_gitignore


class TestGitIgnoreManager:
    """Test suite for GitIgnoreManager class."""

    def test_creates_new_file(self, tmp_path):
        """Test creating new .gitignore file when none exists."""
        manager = GitIgnoreManager(tmp_path)

        added, existing = manager.ensure_entries([".claude-mpm/", ".claude/agents/"])

        # Verify return values
        assert len(added) == 2
        assert ".claude-mpm/" in added
        assert ".claude/agents/" in added
        assert len(existing) == 0

        # Verify file was created
        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()

        # Verify content
        content = gitignore.read_text()
        assert ".claude-mpm/" in content
        assert ".claude/agents/" in content
        assert "# Claude MPM configuration" in content

    def test_avoids_duplicates(self, tmp_path):
        """Test that entries aren't duplicated when already present."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".claude-mpm/\n")

        manager = GitIgnoreManager(tmp_path)
        added, existing = manager.ensure_entries([".claude-mpm/", ".claude/agents/"])

        # Only .claude/agents/ should be added
        assert added == [".claude/agents/"]
        assert existing == [".claude-mpm/"]

        # Verify no duplicate in file
        content = gitignore.read_text()
        assert content.count(".claude-mpm/") == 1
        assert ".claude/agents/" in content

    def test_preserves_existing_content(self, tmp_path):
        """Test that existing .gitignore content is preserved."""
        gitignore = tmp_path / ".gitignore"
        original_content = "# Existing content\n*.pyc\n__pycache__/\n"
        gitignore.write_text(original_content)

        manager = GitIgnoreManager(tmp_path)
        manager.ensure_entries([".claude-mpm/"])

        content = gitignore.read_text()

        # Original content should be preserved
        assert "# Existing content" in content
        assert "*.pyc" in content
        assert "__pycache__/" in content

        # New content should be appended
        assert ".claude-mpm/" in content

    def test_handles_missing_trailing_newline(self, tmp_path):
        """Test handling of .gitignore without trailing newline."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc")  # No trailing newline

        manager = GitIgnoreManager(tmp_path)
        manager.ensure_entries([".claude-mpm/"])

        content = gitignore.read_text()

        # Should add newline before new section
        lines = content.split("\n")
        assert "*.pyc" in lines[0]
        assert any(".claude-mpm/" in line for line in lines)

    def test_handles_comments_and_blank_lines(self, tmp_path):
        """Test that comments and blank lines are handled correctly."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(
            "# Python\n*.pyc\n\n# Node\nnode_modules/\n\n# Empty lines above\n"
        )

        manager = GitIgnoreManager(tmp_path)
        added, existing = manager.ensure_entries(["*.pyc", ".claude-mpm/"])

        # *.pyc should be detected as existing (ignoring comment lines)
        assert "*.pyc" in existing
        assert ".claude-mpm/" in added

    def test_strips_whitespace_when_comparing(self, tmp_path):
        """Test that whitespace is stripped when comparing entries."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("  .claude-mpm/  \n")  # Whitespace around entry

        manager = GitIgnoreManager(tmp_path)
        added, existing = manager.ensure_entries([".claude-mpm/"])

        # Should recognize as existing despite whitespace
        assert ".claude-mpm/" in existing
        assert len(added) == 0

    def test_handles_empty_file(self, tmp_path):
        """Test handling of empty .gitignore file."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("")

        manager = GitIgnoreManager(tmp_path)
        added, existing = manager.ensure_entries([".claude-mpm/"])

        assert ".claude-mpm/" in added
        assert len(existing) == 0

        content = gitignore.read_text()
        assert ".claude-mpm/" in content

    def test_multiple_calls_idempotent(self, tmp_path):
        """Test that multiple calls with same entries are idempotent."""
        manager = GitIgnoreManager(tmp_path)

        # First call
        added1, existing1 = manager.ensure_entries([".claude-mpm/"])
        assert ".claude-mpm/" in added1
        assert len(existing1) == 0

        # Second call
        added2, existing2 = manager.ensure_entries([".claude-mpm/"])
        assert len(added2) == 0
        assert ".claude-mpm/" in existing2

        # Verify file only has one entry
        content = (tmp_path / ".gitignore").read_text()
        assert content.count(".claude-mpm/") == 1

    def test_handles_unicode_content(self, tmp_path):
        """Test handling of unicode characters in .gitignore."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("# Comentário em português\n*.pyc\n", encoding="utf-8")

        manager = GitIgnoreManager(tmp_path)
        added, _existing = manager.ensure_entries([".claude-mpm/"])

        assert ".claude-mpm/" in added

        content = gitignore.read_text(encoding="utf-8")
        assert "Comentário" in content
        assert ".claude-mpm/" in content

    def test_section_header_formatting(self, tmp_path):
        """Test that section header is added with proper formatting."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n")

        manager = GitIgnoreManager(tmp_path)
        manager.ensure_entries([".claude-mpm/"])

        content = gitignore.read_text()
        lines = content.split("\n")

        # Should have blank line, then header, then entry
        assert "# Claude MPM configuration" in content
        header_idx = next(
            i for i, line in enumerate(lines) if "Claude MPM configuration" in line
        )

        # Line before header should be blank (for separation)
        assert lines[header_idx - 1].strip() == ""

        # Line after header should be an entry
        assert ".claude-mpm/" in lines[header_idx + 1]

    def test_new_file_no_extra_blank_line(self, tmp_path):
        """Test that new .gitignore file doesn't start with blank line."""
        manager = GitIgnoreManager(tmp_path)
        manager.ensure_entries([".claude-mpm/"])

        content = (tmp_path / ".gitignore").read_text()
        lines = content.split("\n")

        # First line should be the header, not a blank line
        assert lines[0] == "# Claude MPM configuration"


class TestEnsureClaudeMpmGitignore:
    """Test suite for high-level ensure_claude_mpm_gitignore() function."""

    def test_basic_usage(self, tmp_path):
        """Test basic usage of ensure_claude_mpm_gitignore()."""
        result = ensure_claude_mpm_gitignore(str(tmp_path))

        assert result["status"] == "success"
        assert len(result["added"]) == 2
        assert ".claude-mpm/" in result["added"]
        assert ".claude/agents/" in result["added"]
        assert result["gitignore_path"] == str(tmp_path / ".gitignore")

    def test_with_existing_gitignore(self, tmp_path):
        """Test with existing .gitignore containing one entry."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".claude-mpm/\n")

        result = ensure_claude_mpm_gitignore(str(tmp_path))

        assert result["status"] == "success"
        assert ".claude/agents/" in result["added"]
        assert ".claude-mpm/" in result["existing"]

    def test_all_entries_exist(self, tmp_path):
        """Test when all entries already exist."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".claude-mpm/\n.claude/agents/\n")

        result = ensure_claude_mpm_gitignore(str(tmp_path))

        assert result["status"] == "success"
        assert len(result["added"]) == 0
        assert len(result["existing"]) == 2

    def test_default_current_directory(self, tmp_path, monkeypatch):
        """Test using default current directory."""
        monkeypatch.chdir(tmp_path)

        result = ensure_claude_mpm_gitignore()  # No argument

        assert result["status"] == "success"
        assert len(result["added"]) == 2
        assert (tmp_path / ".gitignore").exists()

    def test_permission_error_handling(self, tmp_path):
        """Test handling of permission errors."""
        # Create read-only directory (requires special handling on Windows)
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("# Existing content\n")
        gitignore.chmod(0o444)  # Read-only

        result = ensure_claude_mpm_gitignore(str(tmp_path))

        # Should return error status
        assert result["status"] == "error"
        assert "Permission denied" in result["error"]
        assert len(result["added"]) == 0

        # Cleanup
        gitignore.chmod(0o644)

    def test_nonexistent_directory(self):
        """Test handling of nonexistent project directory."""
        result = ensure_claude_mpm_gitignore("/nonexistent/path/to/project")

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_very_large_gitignore(self, tmp_path):
        """Test handling of very large .gitignore file (performance test)."""
        gitignore = tmp_path / ".gitignore"

        # Create large .gitignore with 1000 entries
        large_content = "\n".join([f"pattern_{i}/" for i in range(1000)])
        gitignore.write_text(large_content)

        manager = GitIgnoreManager(tmp_path)
        added, existing = manager.ensure_entries([".claude-mpm/"])

        assert ".claude-mpm/" in added
        assert len(existing) == 0

        # Verify original content preserved
        content = gitignore.read_text()
        assert "pattern_500/" in content
        assert ".claude-mpm/" in content

    def test_binary_gitignore_handling(self, tmp_path):
        """Test handling of binary .gitignore file."""
        gitignore = tmp_path / ".gitignore"

        # Write binary data that cannot be decoded as UTF-8
        # Use invalid UTF-8 sequences
        gitignore.write_bytes(b"\xff\xfe\xfd\xfc")

        manager = GitIgnoreManager(tmp_path)

        # Should handle gracefully (log warning and return empty)
        existing = manager._read_existing_entries()
        assert len(existing) == 0

    def test_gitignore_with_patterns_similar_to_claude_mpm(self, tmp_path):
        """Test with patterns similar but not identical to claude-mpm patterns."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".claude/\n.mpm/\n")

        manager = GitIgnoreManager(tmp_path)
        added, existing = manager.ensure_entries([".claude-mpm/", ".claude/agents/"])

        # Both should be added since they're different patterns
        assert ".claude-mpm/" in added
        assert ".claude/agents/" in added
        assert len(existing) == 0

    def test_concurrent_modifications_safety(self, tmp_path):
        """Test that append-only approach is safe for concurrent modifications."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n")

        manager1 = GitIgnoreManager(tmp_path)
        manager2 = GitIgnoreManager(tmp_path)

        # Both managers add entries (simulating concurrent access)
        manager1.ensure_entries([".claude-mpm/"])
        manager2.ensure_entries([".claude/agents/"])

        content = gitignore.read_text()

        # Both entries should be present
        assert ".claude-mpm/" in content
        assert ".claude/agents/" in content
        assert "*.pyc" in content


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    def test_fresh_project_initialization(self, tmp_path):
        """Test initializing a fresh project with no .gitignore."""
        result = ensure_claude_mpm_gitignore(str(tmp_path))

        assert result["status"] == "success"
        assert len(result["added"]) == 2

        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()

        content = gitignore.read_text()
        assert "# Claude MPM configuration" in content
        assert ".claude-mpm/" in content
        assert ".claude/agents/" in content

    def test_existing_project_with_standard_gitignore(self, tmp_path):
        """Test adding to existing project with standard .gitignore."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(
            """# Python
*.pyc
__pycache__/
*.pyo
*.egg-info/

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
"""
        )

        result = ensure_claude_mpm_gitignore(str(tmp_path))

        assert result["status"] == "success"
        assert len(result["added"]) == 2

        content = gitignore.read_text()

        # All original content preserved
        assert "# Python" in content
        assert "*.pyc" in content
        assert ".DS_Store" in content

        # New content added with proper formatting
        assert "# Claude MPM configuration" in content
        assert ".claude-mpm/" in content
        assert ".claude/agents/" in content

    def test_repeated_initialization_idempotent(self, tmp_path):
        """Test that repeated initialization is idempotent."""
        # First initialization
        result1 = ensure_claude_mpm_gitignore(str(tmp_path))
        assert len(result1["added"]) == 2

        # Second initialization
        result2 = ensure_claude_mpm_gitignore(str(tmp_path))
        assert len(result2["added"]) == 0
        assert len(result2["existing"]) == 2

        # Third initialization
        result3 = ensure_claude_mpm_gitignore(str(tmp_path))
        assert len(result3["added"]) == 0
        assert len(result3["existing"]) == 2

        # File should only have entries once
        content = (tmp_path / ".gitignore").read_text()
        assert content.count(".claude-mpm/") == 1
        assert content.count(".claude/agents/") == 1
