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
    PM_CORE_SKILLS,
    add_user_requested_skill,
    cleanup_orphan_skills,
    get_required_skills_from_agents,
    get_skills_from_agent,
    get_user_requested_skills,
    is_user_requested_skill,
    load_deployment_index,
    parse_agent_frontmatter,
    remove_user_requested_skill,
    save_deployment_index,
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

        # Should collect unique skills across all agents + PM_CORE_SKILLS
        expected = {"skill-a", "skill-b", "skill-c", "skill-d"} | PM_CORE_SKILLS
        assert result == expected

    def test_scan_empty_directory(self, tmp_path):
        """Test scanning empty directory."""
        agents_dir = tmp_path / "empty"
        agents_dir.mkdir()

        result = get_required_skills_from_agents(agents_dir)
        # Even empty directory should have PM_CORE_SKILLS
        assert result == PM_CORE_SKILLS

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
        expected = {"skill-a"} | PM_CORE_SKILLS
        assert result == expected

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
        # Should only get skills from valid agent + PM_CORE_SKILLS
        expected = {"skill-a"} | PM_CORE_SKILLS
        assert result == expected

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
        # skill-a should appear only once + PM_CORE_SKILLS
        expected = {"skill-a", "skill-b", "skill-c"} | PM_CORE_SKILLS
        assert result == expected

    def test_slash_to_dash_normalization(self, tmp_path):
        """Test that skill paths with slashes are normalized to dashes.

        WHY: Some skills may use slash format in agent frontmatter,
        but deployment expects "toolchains-python-frameworks-django" for matching.
        This ensures compatibility between skill discovery and deployment filtering.
        """
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Create agent file with slash-separated skill names
        (agents_dir / "agent1.md").write_text(
            """---
skills:
  - explicit-skill
  - toolchains/python/frameworks/django
  - universal/collaboration/git-workflow
---
# Agent 1
"""
        )

        result = get_required_skills_from_agents(agents_dir)

        # Verify slash-separated paths are normalized to dashes
        expected = {
            "explicit-skill",
            "toolchains-python-frameworks-django",
            "universal-collaboration-git-workflow",
        } | PM_CORE_SKILLS
        assert result == expected

        # Ensure no slash-separated paths remain
        for skill in result:
            assert "/" not in skill, f"Skill {skill} contains unprocessed slashes"

    def test_pm_core_skills_always_included(self, tmp_path):
        """Test that PM_CORE_SKILLS are always included in results.

        WHY: PM_INSTRUCTIONS.md contains [SKILL: name] markers referencing PM core skills.
        Without these skills deployed, PM only sees placeholders, not actual content.
        This test ensures PM core skills are always included regardless of agent declarations.
        """
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Create agent with no PM skills declared
        (agents_dir / "agent1.md").write_text(
            """---
name: agent1
skills:
  - some-other-skill
---
# Agent 1
"""
        )

        result = get_required_skills_from_agents(agents_dir)

        # Verify all PM_CORE_SKILLS are present
        for pm_skill in PM_CORE_SKILLS:
            assert (
                pm_skill in result
            ), f"PM core skill {pm_skill} should always be included"

        # Verify the agent's skill is also present
        assert "some-other-skill" in result

    def test_pm_core_skills_included_even_with_empty_agents(self, tmp_path):
        """Test PM_CORE_SKILLS included even when no agents have skills."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Create agent with no skills
        (agents_dir / "agent1.md").write_text(
            """---
name: agent1
---
# Agent 1
"""
        )

        result = get_required_skills_from_agents(agents_dir)

        # PM_CORE_SKILLS should still be present
        assert PM_CORE_SKILLS.issubset(
            result
        ), "PM core skills should be included even with no agent-declared skills"


class TestUserRequestedSkills:
    """Test user-requested skills management."""

    def test_add_user_requested_skill(self, tmp_path):
        """Test adding a skill to user_requested_skills."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Add skill
        result = add_user_requested_skill("django-framework", claude_skills_dir)
        assert result is True

        # Verify it was added to index
        user_requested = get_user_requested_skills(claude_skills_dir)
        assert "django-framework" in user_requested

    def test_add_duplicate_user_requested_skill(self, tmp_path):
        """Test adding a skill that's already user-requested."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Add skill twice
        add_user_requested_skill("django-framework", claude_skills_dir)
        result = add_user_requested_skill("django-framework", claude_skills_dir)

        # Second add should return False (already exists)
        assert result is False

        # Should only appear once
        user_requested = get_user_requested_skills(claude_skills_dir)
        assert user_requested.count("django-framework") == 1

    def test_remove_user_requested_skill(self, tmp_path):
        """Test removing a skill from user_requested_skills."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Add then remove skill
        add_user_requested_skill("django-framework", claude_skills_dir)
        result = remove_user_requested_skill("django-framework", claude_skills_dir)
        assert result is True

        # Verify it was removed
        user_requested = get_user_requested_skills(claude_skills_dir)
        assert "django-framework" not in user_requested

    def test_remove_nonexistent_user_requested_skill(self, tmp_path):
        """Test removing a skill that's not user-requested."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Try to remove skill that was never added
        result = remove_user_requested_skill("nonexistent-skill", claude_skills_dir)
        assert result is False

    def test_is_user_requested_skill(self, tmp_path):
        """Test checking if a skill is user-requested."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Add skill
        add_user_requested_skill("django-framework", claude_skills_dir)

        # Check presence
        assert is_user_requested_skill("django-framework", claude_skills_dir) is True
        assert is_user_requested_skill("not-requested", claude_skills_dir) is False

    def test_get_user_requested_skills_empty(self, tmp_path):
        """Test getting user_requested_skills from empty index."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        user_requested = get_user_requested_skills(claude_skills_dir)
        assert user_requested == []

    def test_get_user_requested_skills_multiple(self, tmp_path):
        """Test getting multiple user-requested skills."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Add multiple skills
        add_user_requested_skill("django-framework", claude_skills_dir)
        add_user_requested_skill("fastapi-patterns", claude_skills_dir)
        add_user_requested_skill("playwright-e2e-testing", claude_skills_dir)

        user_requested = get_user_requested_skills(claude_skills_dir)
        assert len(user_requested) == 3
        assert "django-framework" in user_requested
        assert "fastapi-patterns" in user_requested
        assert "playwright-e2e-testing" in user_requested


class TestCleanupOrphanSkillsWithUserRequested:
    """Test orphan cleanup respects user-requested skills."""

    def test_cleanup_preserves_user_requested_skills(self, tmp_path):
        """Test that user-requested skills are never cleaned up as orphans."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Create index with deployed skills
        index = {
            "deployed_skills": {
                "agent-skill": {
                    "collection": "test",
                    "deployed_at": "2025-01-01T00:00:00Z",
                },
                "user-skill": {
                    "collection": "test",
                    "deployed_at": "2025-01-01T00:00:00Z",
                },
                "orphan-skill": {
                    "collection": "test",
                    "deployed_at": "2025-01-01T00:00:00Z",
                },
            },
            "user_requested_skills": ["user-skill"],
            "last_sync": "2025-01-01T00:00:00Z",
        }
        save_deployment_index(claude_skills_dir, index)

        # Create skill directories
        (claude_skills_dir / "agent-skill").mkdir()
        (claude_skills_dir / "user-skill").mkdir()
        (claude_skills_dir / "orphan-skill").mkdir()

        # Cleanup with only agent-skill required
        required_skills = {"agent-skill"}
        result = cleanup_orphan_skills(claude_skills_dir, required_skills)

        # user-skill should be preserved (user-requested)
        # orphan-skill should be removed
        assert result["removed_count"] == 1
        assert "orphan-skill" in result["removed_skills"]
        assert (claude_skills_dir / "user-skill").exists()
        assert not (claude_skills_dir / "orphan-skill").exists()

    def test_cleanup_with_no_user_requested_skills(self, tmp_path):
        """Test cleanup works normally when no user-requested skills exist."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Create index without user-requested skills
        index = {
            "deployed_skills": {
                "agent-skill": {
                    "collection": "test",
                    "deployed_at": "2025-01-01T00:00:00Z",
                },
                "orphan-skill": {
                    "collection": "test",
                    "deployed_at": "2025-01-01T00:00:00Z",
                },
            },
            "user_requested_skills": [],
            "last_sync": "2025-01-01T00:00:00Z",
        }
        save_deployment_index(claude_skills_dir, index)

        # Create skill directories
        (claude_skills_dir / "agent-skill").mkdir()
        (claude_skills_dir / "orphan-skill").mkdir()

        # Cleanup with only agent-skill required
        required_skills = {"agent-skill"}
        result = cleanup_orphan_skills(claude_skills_dir, required_skills)

        # orphan-skill should be removed
        assert result["removed_count"] == 1
        assert "orphan-skill" in result["removed_skills"]
        assert not (claude_skills_dir / "orphan-skill").exists()

    def test_cleanup_all_skills_protected(self, tmp_path):
        """Test cleanup when all skills are either required or user-requested."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Create index with skills that are all protected
        index = {
            "deployed_skills": {
                "agent-skill": {
                    "collection": "test",
                    "deployed_at": "2025-01-01T00:00:00Z",
                },
                "user-skill": {
                    "collection": "test",
                    "deployed_at": "2025-01-01T00:00:00Z",
                },
            },
            "user_requested_skills": ["user-skill"],
            "last_sync": "2025-01-01T00:00:00Z",
        }
        save_deployment_index(claude_skills_dir, index)

        # Create skill directories
        (claude_skills_dir / "agent-skill").mkdir()
        (claude_skills_dir / "user-skill").mkdir()

        # Cleanup with agent-skill required
        required_skills = {"agent-skill"}
        result = cleanup_orphan_skills(claude_skills_dir, required_skills)

        # Nothing should be removed
        assert result["removed_count"] == 0
        assert result["removed_skills"] == []
        assert (claude_skills_dir / "agent-skill").exists()
        assert (claude_skills_dir / "user-skill").exists()


class TestDeploymentIndexBackwardCompatibility:
    """Test backward compatibility of deployment index loading."""

    def test_load_old_index_without_user_requested_skills(self, tmp_path):
        """Test loading index from old version without user_requested_skills field."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Create old-format index (no user_requested_skills)
        import json

        index_path = claude_skills_dir / ".mpm-deployed-skills.json"
        index_path.write_text(
            json.dumps(
                {
                    "deployed_skills": {
                        "skill-a": {
                            "collection": "test",
                            "deployed_at": "2025-01-01T00:00:00Z",
                        }
                    },
                    "last_sync": "2025-01-01T00:00:00Z",
                }
            )
        )

        # Load index - should add empty user_requested_skills
        index = load_deployment_index(claude_skills_dir)
        assert "user_requested_skills" in index
        assert index["user_requested_skills"] == []

    def test_save_and_load_index_preserves_user_requested(self, tmp_path):
        """Test that saving and loading preserves user_requested_skills."""
        claude_skills_dir = tmp_path / "skills"
        claude_skills_dir.mkdir()

        # Create index with user-requested skills
        index = {
            "deployed_skills": {
                "skill-a": {"collection": "test", "deployed_at": "2025-01-01T00:00:00Z"}
            },
            "user_requested_skills": ["skill-b", "skill-c"],
            "last_sync": "2025-01-01T00:00:00Z",
        }

        # Save and reload
        save_deployment_index(claude_skills_dir, index)
        loaded = load_deployment_index(claude_skills_dir)

        # Verify user_requested_skills preserved
        assert loaded["user_requested_skills"] == ["skill-b", "skill-c"]
