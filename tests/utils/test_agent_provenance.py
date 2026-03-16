"""Tests for agent provenance detection utilities.

Test Coverage:
- is_mpm_managed_agent(): YAML frontmatter author detection
- is_mpm_managed_file(): file-based convenience wrapper
- MPM_AUTHOR_PATTERNS: canonical frozenset of recognised authors
- The key bug fix: body text mentioning claude-mpm must NOT trigger detection
"""

from pathlib import Path

import pytest

from claude_mpm.utils.agent_provenance import (
    MPM_AUTHOR_PATTERNS,
    is_mpm_managed_agent,
    is_mpm_managed_file,
)


class TestIsMpmManagedAgent:
    """Tests for the canonical provenance detection function."""

    def test_standard_mpm_agent(self):
        """Agent with author: claude-mpm in frontmatter is detected."""
        content = "---\nname: Test\nauthor: claude-mpm\nversion: 1.0.0\n---\nBody text"
        assert is_mpm_managed_agent(content) is True

    def test_quoted_author_single(self):
        """Agent with author: 'claude-mpm' (single quotes) is detected."""
        content = "---\nname: Test\nauthor: 'claude-mpm'\n---\nBody"
        assert is_mpm_managed_agent(content) is True

    def test_quoted_author_double(self):
        """Agent with author: \"claude-mpm\" (double quotes) is detected."""
        content = '---\nname: Test\nauthor: "claude-mpm"\n---\nBody'
        assert is_mpm_managed_agent(content) is True

    def test_anthropic_author(self):
        """Agent with author: anthropic in frontmatter is detected."""
        content = "---\nname: Test\nauthor: anthropic\n---\nBody"
        assert is_mpm_managed_agent(content) is True

    def test_claude_mpm_space(self):
        """Agent with author: claude mpm (with space) is detected."""
        content = "---\nname: Test\nauthor: claude mpm\n---\nBody"
        assert is_mpm_managed_agent(content) is True

    def test_email_author(self):
        """Agent with author: claude-mpm@anthropic.com is detected."""
        content = "---\nname: Test\nauthor: claude-mpm@anthropic.com\n---\nBody"
        assert is_mpm_managed_agent(content) is True

    def test_case_insensitive(self):
        """Author matching is case-insensitive."""
        content = "---\nname: Test\nauthor: Claude-MPM\n---\nBody"
        assert is_mpm_managed_agent(content) is True

    def test_claude_mpm_in_body_only_not_detected(self):
        """THE KEY BUG FIX: agent mentioning claude-mpm in body only is NOT MPM-managed."""
        content = "---\nname: Test\nauthor: custom-user\n---\nThis agent works with claude-mpm for orchestration."
        assert is_mpm_managed_agent(content) is False

    def test_author_claude_mpm_in_body_not_detected(self):
        """Body containing 'author: claude-mpm' string is NOT detected."""
        content = (
            "---\nname: My Custom Agent\nauthor: john-doe\n---\n\n"
            "# My Agent\n\n"
            "This agent integrates with claude-mpm for multi-agent workflows.\n"
            "It uses author: claude-mpm patterns internally.\n"
        )
        assert is_mpm_managed_agent(content) is False

    def test_no_frontmatter(self):
        """File with no frontmatter delimiters returns False."""
        content = "# Just a markdown file\nauthor: claude-mpm"
        assert is_mpm_managed_agent(content) is False

    def test_no_author_field(self):
        """Frontmatter without author field returns False."""
        content = "---\nname: Test\nversion: 1.0.0\n---\nBody"
        assert is_mpm_managed_agent(content) is False

    def test_empty_content(self):
        """Empty string returns False."""
        assert is_mpm_managed_agent("") is False

    def test_incomplete_frontmatter(self):
        """Frontmatter with only opening delimiter returns False."""
        content = "---\nname: Test\nauthor: claude-mpm"
        assert is_mpm_managed_agent(content) is False

    def test_non_mpm_author(self):
        """Agent with a custom author returns False."""
        content = "---\nname: Test\nauthor: my-custom-author\n---\nBody"
        assert is_mpm_managed_agent(content) is False

    def test_empty_author(self):
        """Agent with empty author field returns False."""
        content = "---\nname: Test\nauthor:\n---\nBody"
        assert is_mpm_managed_agent(content) is False

    def test_author_with_extra_whitespace(self):
        """Author field with extra whitespace is handled."""
        content = "---\nname: Test\nauthor:   claude-mpm  \n---\nBody"
        assert is_mpm_managed_agent(content) is True

    def test_frontmatter_only_no_body(self):
        """Agent with frontmatter but empty body is detected."""
        content = "---\nname: Test\nauthor: claude-mpm\n---\n"
        assert is_mpm_managed_agent(content) is True

    def test_multiple_dashes_in_body(self):
        """Body containing --- doesn't confuse frontmatter parsing."""
        content = "---\nname: Test\nauthor: claude-mpm\n---\n\nSome text\n---\nauthor: other\n---\n"
        assert is_mpm_managed_agent(content) is True


class TestIsMpmManagedFile:
    """Tests for the file-based convenience wrapper."""

    def test_mpm_managed_file(self, tmp_path):
        """File with MPM author is detected."""
        agent_file = tmp_path / "test_agent.md"
        agent_file.write_text("---\nname: Test\nauthor: claude-mpm\n---\nBody")
        assert is_mpm_managed_file(agent_file) is True

    def test_user_created_file(self, tmp_path):
        """File with custom author is not MPM-managed."""
        agent_file = tmp_path / "test_agent.md"
        agent_file.write_text("---\nname: Test\nauthor: user123\n---\nBody")
        assert is_mpm_managed_file(agent_file) is False

    def test_nonexistent_file(self, tmp_path):
        """Non-existent file returns False (no exception)."""
        agent_file = tmp_path / "does_not_exist.md"
        assert is_mpm_managed_file(agent_file) is False

    def test_unreadable_file(self, tmp_path):
        """File that can't be read returns False (no exception)."""
        agent_file = tmp_path / "unreadable.md"
        agent_file.write_text("---\nauthor: claude-mpm\n---\n")
        agent_file.chmod(0o000)
        try:
            assert is_mpm_managed_file(agent_file) is False
        finally:
            agent_file.chmod(0o644)  # restore for cleanup


class TestMpmAuthorPatterns:
    """Tests for the canonical pattern set."""

    def test_patterns_is_frozenset(self):
        """Patterns are immutable."""
        assert isinstance(MPM_AUTHOR_PATTERNS, frozenset)

    def test_expected_patterns_present(self):
        """All expected patterns are in the set."""
        assert "claude-mpm" in MPM_AUTHOR_PATTERNS
        assert "claude mpm" in MPM_AUTHOR_PATTERNS
        assert "anthropic" in MPM_AUTHOR_PATTERNS
        assert "claude-mpm@anthropic.com" in MPM_AUTHOR_PATTERNS
