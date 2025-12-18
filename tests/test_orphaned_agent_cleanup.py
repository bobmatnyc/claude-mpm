"""
Test orphaned agent cleanup functionality.

This test verifies that the cleanup function correctly:
1. Removes claude-mpm managed agents that are no longer deployed
2. Preserves user-created agents without frontmatter
3. Preserves user-created agents without ownership markers
"""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.cli.startup import _cleanup_orphaned_agents


@pytest.fixture
def temp_agents_dir():
    """Create a temporary agents directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_cleanup_removes_orphaned_claude_mpm_agents(temp_agents_dir):
    """Test that orphaned claude-mpm agents are removed."""
    # Create a claude-mpm agent with frontmatter
    orphaned_agent = temp_agents_dir / "orphaned-agent.md"
    orphaned_agent.write_text(
        """---
agent_id: test-orphaned-agent
author: Claude MPM Team
source: remote
version: 1.0.0
---

# Orphaned Agent

This agent should be removed.
"""
    )

    # Create another claude-mpm agent that should remain
    deployed_agent = temp_agents_dir / "deployed-agent.md"
    deployed_agent.write_text(
        """---
agent_id: test-deployed-agent
author: Claude MPM Team
source: remote
version: 1.0.0
---

# Deployed Agent

This agent should remain.
"""
    )

    # Run cleanup with only deployed-agent in the list
    removed = _cleanup_orphaned_agents(temp_agents_dir, ["deployed-agent.md"])

    # Verify results
    assert removed == 1
    assert not orphaned_agent.exists()
    assert deployed_agent.exists()


def test_cleanup_preserves_user_agents_without_frontmatter(temp_agents_dir):
    """Test that user agents without frontmatter are preserved."""
    # Create a user agent without frontmatter
    user_agent = temp_agents_dir / "my-custom-agent.md"
    user_agent.write_text(
        """# My Custom Agent

This is a user-created agent without frontmatter.
"""
    )

    # Run cleanup (should not remove user agent)
    removed = _cleanup_orphaned_agents(temp_agents_dir, [])

    # Verify user agent was preserved
    assert removed == 0
    assert user_agent.exists()


def test_cleanup_preserves_user_agents_with_custom_frontmatter(temp_agents_dir):
    """Test that user agents with custom frontmatter are preserved."""
    # Create a user agent with custom frontmatter (no ownership markers)
    user_agent = temp_agents_dir / "my-custom-agent.md"
    user_agent.write_text(
        """---
name: My Custom Agent
version: 1.0.0
author: John Doe
---

# My Custom Agent

This is a user-created agent with custom frontmatter.
"""
    )

    # Run cleanup (should not remove user agent)
    removed = _cleanup_orphaned_agents(temp_agents_dir, [])

    # Verify user agent was preserved
    assert removed == 0
    assert user_agent.exists()


def test_cleanup_with_multiple_ownership_markers(temp_agents_dir):
    """Test cleanup with different ownership marker combinations."""
    # Create agents with different markers
    agent_with_author = temp_agents_dir / "agent-author.md"
    agent_with_author.write_text(
        """---
author: Claude MPM Team
---

# Agent with Author
"""
    )

    agent_with_source = temp_agents_dir / "agent-source.md"
    agent_with_source.write_text(
        """---
source: remote
---

# Agent with Source
"""
    )

    agent_with_id = temp_agents_dir / "agent-id.md"
    agent_with_id.write_text(
        """---
agent_id: test-agent
---

# Agent with ID
"""
    )

    # Run cleanup (none should remain)
    removed = _cleanup_orphaned_agents(temp_agents_dir, [])

    # All should be removed
    assert removed == 3
    assert not agent_with_author.exists()
    assert not agent_with_source.exists()
    assert not agent_with_id.exists()


def test_cleanup_skips_hidden_files(temp_agents_dir):
    """Test that hidden files are skipped."""
    # Create a hidden file
    hidden_file = temp_agents_dir / ".hidden-agent.md"
    hidden_file.write_text(
        """---
agent_id: hidden-agent
author: Claude MPM Team
---

# Hidden Agent
"""
    )

    # Run cleanup
    removed = _cleanup_orphaned_agents(temp_agents_dir, [])

    # Hidden file should not be removed
    assert removed == 0
    assert hidden_file.exists()


def test_cleanup_handles_invalid_yaml(temp_agents_dir):
    """Test that cleanup handles agents with invalid YAML gracefully."""
    # Create an agent with invalid YAML frontmatter
    invalid_agent = temp_agents_dir / "invalid-agent.md"
    invalid_agent.write_text(
        """---
agent_id: test
author: Claude MPM Team
invalid yaml: [unclosed bracket
---

# Invalid Agent
"""
    )

    # Run cleanup (should not crash, should skip file)
    removed = _cleanup_orphaned_agents(temp_agents_dir, [])

    # Should preserve file if YAML parsing fails (safety first)
    assert removed == 0
    assert invalid_agent.exists()


def test_cleanup_with_empty_directory(temp_agents_dir):
    """Test cleanup with empty directory."""
    # Run cleanup on empty directory
    removed = _cleanup_orphaned_agents(temp_agents_dir, [])

    # Should return 0
    assert removed == 0


def test_cleanup_with_nonexistent_directory():
    """Test cleanup with nonexistent directory."""
    # Run cleanup on nonexistent directory
    nonexistent = Path("/tmp/nonexistent-agents-dir-12345")
    removed = _cleanup_orphaned_agents(nonexistent, [])

    # Should return 0 without error
    assert removed == 0
