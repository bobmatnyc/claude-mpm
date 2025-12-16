"""Tests for selective skill deployment.

WHY: Ensures selective skill deployment correctly parses agent frontmatter
and filters skills based on agent requirements. Validates both legacy and
new skills field formats.

DESIGN DECISIONS:
- Test both legacy flat list and new required/optional dict formats
- Mock file system operations to avoid dependency on actual files
- Test edge cases (empty, None, invalid formats)
- Verify integration with agent scanning logic
"""

from pathlib import Path

import pytest

from claude_mpm.services.skills.selective_skill_deployer import (
    get_required_skills_from_agents,
    get_skills_from_agent,
    parse_agent_frontmatter,
)


class TestParseAgentFrontmatter:
    """Test YAML frontmatter parsing from agent markdown files."""

    def test_parse_valid_frontmatter(self, tmp_path):
        """Test parsing valid YAML frontmatter."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text(
            """---
name: test-agent
skills:
  - skill-a
  - skill-b
version: "1.0.0"
---
# Agent Content
This is the agent description.
"""
        )

        result = parse_agent_frontmatter(agent_file)
        assert result["name"] == "test-agent"
        assert result["skills"] == ["skill-a", "skill-b"]
        assert result["version"] == "1.0.0"

    def test_parse_no_frontmatter(self, tmp_path):
        """Test parsing file with no frontmatter."""
        agent_file = tmp_path / "no-frontmatter.md"
        agent_file.write_text("# Agent Content\nNo frontmatter here.")

        result = parse_agent_frontmatter(agent_file)
        assert result == {}

    def test_parse_invalid_yaml(self, tmp_path):
        """Test parsing invalid YAML frontmatter."""
        agent_file = tmp_path / "invalid.md"
        agent_file.write_text(
            """---
invalid: yaml: syntax: error:
---
# Agent Content
"""
        )

        result = parse_agent_frontmatter(agent_file)
        assert result == {}

    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing nonexistent file."""
        agent_file = tmp_path / "nonexistent.md"

        result = parse_agent_frontmatter(agent_file)
        assert result == {}


class TestGetSkillsFromAgent:
    """Test skill extraction from agent frontmatter."""

    def test_legacy_flat_list_format(self):
        """Test parsing legacy flat list format."""
        frontmatter = {"skills": ["skill-a", "skill-b", "skill-c"]}

        result = get_skills_from_agent(frontmatter)
        assert result == {"skill-a", "skill-b", "skill-c"}

    def test_new_required_optional_format(self):
        """Test parsing new required/optional format."""
        frontmatter = {
            "skills": {"required": ["skill-a", "skill-b"], "optional": ["skill-c"]}
        }

        result = get_skills_from_agent(frontmatter)
        assert result == {"skill-a", "skill-b", "skill-c"}

    def test_new_format_required_only(self):
        """Test new format with only required skills."""
        frontmatter = {"skills": {"required": ["skill-a", "skill-b"]}}

        result = get_skills_from_agent(frontmatter)
        assert result == {"skill-a", "skill-b"}

    def test_new_format_optional_only(self):
        """Test new format with only optional skills."""
        frontmatter = {"skills": {"optional": ["skill-c"]}}

        result = get_skills_from_agent(frontmatter)
        assert result == {"skill-c"}

    def test_new_format_empty_lists(self):
        """Test new format with empty lists."""
        frontmatter = {"skills": {"required": [], "optional": []}}

        result = get_skills_from_agent(frontmatter)
        assert result == set()

    def test_empty_frontmatter(self):
        """Test agent with no skills field."""
        frontmatter = {}

        result = get_skills_from_agent(frontmatter)
        assert result == set()

    def test_skills_field_none(self):
        """Test agent with skills: None."""
        frontmatter = {"skills": None}

        result = get_skills_from_agent(frontmatter)
        assert result == set()

    def test_skills_field_empty_list(self):
        """Test agent with empty skills list."""
        frontmatter = {"skills": []}

        result = get_skills_from_agent(frontmatter)
        assert result == set()

    def test_new_format_non_list_values(self):
        """Test new format with non-list values (edge case)."""
        frontmatter = {"skills": {"required": "not-a-list", "optional": None}}

        result = get_skills_from_agent(frontmatter)
        # Should handle gracefully and return empty set
        assert result == set()

    def test_unsupported_format(self):
        """Test unsupported skills field format."""
        frontmatter = {"skills": "invalid-string-format"}

        result = get_skills_from_agent(frontmatter)
        # Should handle gracefully and return empty set
        assert result == set()


class TestGetRequiredSkillsFromAgents:
    """Test scanning agents directory for required skills."""

    def test_scan_agents_directory(self, tmp_path):
        """Test scanning directory with multiple agents."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Agent 1: Legacy format
        (agents_dir / "agent1.md").write_text(
            """---
name: agent1
skills:
  - skill-a
  - skill-b
---
# Agent 1
"""
        )

        # Agent 2: New format
        (agents_dir / "agent2.md").write_text(
            """---
name: agent2
skills:
  required:
    - skill-b
    - skill-c
  optional:
    - skill-d
---
# Agent 2
"""
        )

        # Agent 3: No skills
        (agents_dir / "agent3.md").write_text(
            """---
name: agent3
---
# Agent 3
"""
        )

        result = get_required_skills_from_agents(agents_dir)

        # Should collect unique skills across all agents
        assert result == {"skill-a", "skill-b", "skill-c", "skill-d"}

    def test_scan_empty_directory(self, tmp_path):
        """Test scanning empty directory."""
        agents_dir = tmp_path / "empty"
        agents_dir.mkdir()

        result = get_required_skills_from_agents(agents_dir)
        assert result == set()

    def test_scan_nonexistent_directory(self, tmp_path):
        """Test scanning nonexistent directory."""
        agents_dir = tmp_path / "nonexistent"

        result = get_required_skills_from_agents(agents_dir)
        assert result == set()

    def test_scan_ignores_non_markdown_files(self, tmp_path):
        """Test that scanner ignores non-.md files."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Valid agent
        (agents_dir / "agent.md").write_text(
            """---
name: agent
skills:
  - skill-a
---
# Agent
"""
        )

        # Non-markdown file (should be ignored)
        (agents_dir / "readme.txt").write_text("Not an agent")

        result = get_required_skills_from_agents(agents_dir)
        assert result == {"skill-a"}

    def test_scan_handles_invalid_frontmatter(self, tmp_path):
        """Test that scanner handles agents with invalid frontmatter."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Valid agent
        (agents_dir / "agent1.md").write_text(
            """---
name: agent1
skills:
  - skill-a
---
# Agent 1
"""
        )

        # Invalid frontmatter (should be skipped)
        (agents_dir / "agent2.md").write_text(
            """---
invalid: yaml: syntax:
---
# Agent 2
"""
        )

        result = get_required_skills_from_agents(agents_dir)
        # Should only get skills from valid agent
        assert result == {"skill-a"}

    def test_deduplication_across_agents(self, tmp_path):
        """Test that duplicate skills are deduplicated."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Both agents reference skill-a
        (agents_dir / "agent1.md").write_text(
            """---
skills: [skill-a, skill-b]
---
# Agent 1
"""
        )

        (agents_dir / "agent2.md").write_text(
            """---
skills: [skill-a, skill-c]
---
# Agent 2
"""
        )

        result = get_required_skills_from_agents(agents_dir)
        # skill-a should appear only once
        assert result == {"skill-a", "skill-b", "skill-c"}
