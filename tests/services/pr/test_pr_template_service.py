"""
Unit Tests for PRTemplateService
=================================

Tests PR template generation for agent and skill improvements.
Validates conventional commit format and PR body structure.
"""

import unittest

from claude_mpm.services.pr.pr_template_service import (PRTemplateService,
                                                        PRType)


class TestPRTemplateService(unittest.TestCase):
    """Test suite for PRTemplateService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = PRTemplateService()

    def test_generate_pr_title_agent(self):
        """Test generating PR title for agent."""
        title = self.service.generate_pr_title(
            "research", "improve memory handling", PRType.AGENT
        )

        self.assertEqual(
            title, "feat(agent): improve research - improve memory handling"
        )

    def test_generate_pr_title_skill(self):
        """Test generating PR title for skill."""
        title = self.service.generate_pr_title(
            "fastapi-testing", "add async patterns", PRType.SKILL
        )

        self.assertEqual(
            title, "feat(skill): improve fastapi-testing - add async patterns"
        )

    def test_generate_pr_title_custom_commit_type(self):
        """Test generating PR title with custom commit type."""
        title = self.service.generate_pr_title(
            "research", "fix memory leak", PRType.AGENT, commit_type="fix"
        )

        self.assertEqual(title, "fix(agent): improve research - fix memory leak")

    def test_generate_agent_pr_body(self):
        """Test generating PR body for agent improvement."""
        body = self.service.generate_agent_pr_body(
            agent_name="research",
            problem="Memory exhaustion when analyzing >50 files",
            solution="Add hard limit of 5 files per session",
            testing_notes="Tested with 100-file codebase",
            related_issues=["#157"],
        )

        # Verify key sections are present
        self.assertIn("## Problem Statement", body)
        self.assertIn("Memory exhaustion when analyzing >50 files", body)
        self.assertIn("## Proposed Solution", body)
        self.assertIn("Add hard limit of 5 files per session", body)
        self.assertIn("## Testing Performed", body)
        self.assertIn("Tested with 100-file codebase", body)
        self.assertIn("## Related Issues", body)
        self.assertIn("Closes #157", body)
        self.assertIn("## Checklist", body)
        self.assertIn("agent-improver", body)

    def test_generate_agent_pr_body_no_issues(self):
        """Test generating PR body without related issues."""
        body = self.service.generate_agent_pr_body(
            agent_name="research",
            problem="Problem description",
            solution="Solution description",
            testing_notes="Testing notes",
        )

        # Should not have Related Issues section
        self.assertNotIn("## Related Issues", body)

    def test_generate_agent_pr_body_multiple_issues(self):
        """Test generating PR body with multiple related issues."""
        body = self.service.generate_agent_pr_body(
            agent_name="research",
            problem="Problem",
            solution="Solution",
            testing_notes="Testing",
            related_issues=["#157", "142", "#143"],
        )

        # Verify all issues are included with # prefix
        self.assertIn("Closes #157", body)
        self.assertIn("Closes #142", body)
        self.assertIn("Closes #143", body)

    def test_generate_skill_pr_body(self):
        """Test generating PR body for skill improvement."""
        body = self.service.generate_skill_pr_body(
            skill_name="fastapi-testing",
            improvements="Added async test patterns and database handling",
            justification="Users struggled with async endpoint testing",
            examples="pytest-asyncio config, AsyncClient usage",
            related_issues=["#203"],
        )

        # Verify key sections are present
        self.assertIn("## Skill Enhancement", body)
        self.assertIn("fastapi-testing", body)
        self.assertIn("## Motivation", body)
        self.assertIn("Users struggled with async endpoint testing", body)
        self.assertIn("## Improvements", body)
        self.assertIn("Added async test patterns", body)
        self.assertIn("## Examples Added", body)
        self.assertIn("pytest-asyncio config", body)
        self.assertIn("## Testing", body)
        self.assertIn("## Related Issues", body)
        self.assertIn("Issue #203", body)
        self.assertIn("skills-manager", body)

    def test_generate_skill_pr_body_no_issues(self):
        """Test generating skill PR body without related issues."""
        body = self.service.generate_skill_pr_body(
            skill_name="fastapi-testing",
            improvements="Improvements",
            justification="Justification",
            examples="Examples",
        )

        # Should not have Related Issues section
        self.assertNotIn("## Related Issues", body)

    def test_validate_conventional_commit_valid(self):
        """Test validating valid conventional commit messages."""
        valid_messages = [
            "feat(agent): improve research agent",
            "fix(skill): fix broken example",
            "docs(agent): update documentation",
            "refactor(skill): simplify code structure",
        ]

        for message in valid_messages:
            with self.subTest(message=message):
                self.assertTrue(self.service.validate_conventional_commit(message))

    def test_validate_conventional_commit_with_body(self):
        """Test validating commit message with body."""
        message = """feat(agent): improve research agent

- Add hard limit of 5 files
- Document MCP summarizer
- Update strategic sampling guidance

Addresses user feedback about memory exhaustion.
"""

        self.assertTrue(self.service.validate_conventional_commit(message))

    def test_validate_conventional_commit_invalid(self):
        """Test validating invalid conventional commit messages."""
        invalid_messages = [
            "improve research agent",  # No type(scope)
            "feat improve research",  # No scope
            "feat(): improve research",  # Empty scope
            "feat(agent):",  # No description
            "feat(agent) improve",  # No colon
            "",  # Empty
            "unknown(agent): improve",  # Invalid type
        ]

        for message in invalid_messages:
            with self.subTest(message=message):
                self.assertFalse(self.service.validate_conventional_commit(message))

    def test_generate_commit_message(self):
        """Test generating conventional commit message."""
        message = self.service.generate_commit_message(
            item_name="research",
            brief_description="improve memory efficiency",
            detailed_changes="- Add hard limit of 5 files\n- Document MCP summarizer",
            pr_type=PRType.AGENT,
        )

        # Verify format
        self.assertIn(
            "feat(agent): improve research - improve memory efficiency", message
        )
        self.assertIn("- Add hard limit of 5 files", message)
        self.assertIn("- Document MCP summarizer", message)
        self.assertIn("Generated with Claude MPM", message)

    def test_generate_commit_message_skill(self):
        """Test generating commit message for skill."""
        message = self.service.generate_commit_message(
            item_name="fastapi-testing",
            brief_description="add async patterns",
            detailed_changes="- Add pytest-asyncio examples\n- Document AsyncClient",
            pr_type=PRType.SKILL,
            commit_type="feat",
        )

        self.assertIn("feat(skill):", message)
        self.assertIn("fastapi-testing", message)

    def test_commit_types_available(self):
        """Test that commit types are defined."""
        self.assertIn("feat", self.service.COMMIT_TYPES)
        self.assertIn("fix", self.service.COMMIT_TYPES)
        self.assertIn("docs", self.service.COMMIT_TYPES)
        self.assertIn("refactor", self.service.COMMIT_TYPES)
        self.assertIn("test", self.service.COMMIT_TYPES)
        self.assertIn("chore", self.service.COMMIT_TYPES)

    def test_pr_type_enum(self):
        """Test PRType enum values."""
        self.assertEqual(PRType.AGENT.value, "agent")
        self.assertEqual(PRType.SKILL.value, "skill")

    def test_agent_pr_body_structure(self):
        """Test that agent PR body has all required sections."""
        body = self.service.generate_agent_pr_body(
            agent_name="test",
            problem="test problem",
            solution="test solution",
            testing_notes="test testing",
        )

        required_sections = [
            "## Problem Statement",
            "## Proposed Solution",
            "## Changes Made",
            "## Testing Performed",
            "## Checklist",
        ]

        for section in required_sections:
            with self.subTest(section=section):
                self.assertIn(section, body)

    def test_skill_pr_body_structure(self):
        """Test that skill PR body has all required sections."""
        body = self.service.generate_skill_pr_body(
            skill_name="test",
            improvements="test improvements",
            justification="test justification",
            examples="test examples",
        )

        required_sections = [
            "## Skill Enhancement",
            "## Motivation",
            "## Improvements",
            "## Examples Added",
            "## Testing",
        ]

        for section in required_sections:
            with self.subTest(section=section):
                self.assertIn(section, body)

    def test_pr_body_has_checkboxes(self):
        """Test that PR bodies include checkboxes."""
        agent_body = self.service.generate_agent_pr_body(
            agent_name="test",
            problem="problem",
            solution="solution",
            testing_notes="testing",
        )

        skill_body = self.service.generate_skill_pr_body(
            skill_name="test",
            improvements="improvements",
            justification="justification",
            examples="examples",
        )

        # Both should have checkboxes
        self.assertIn("- [x]", agent_body)
        self.assertIn("- [x]", skill_body)

    def test_pr_body_has_bot_signature(self):
        """Test that PR bodies include bot signature."""
        agent_body = self.service.generate_agent_pr_body(
            agent_name="test",
            problem="problem",
            solution="solution",
            testing_notes="testing",
        )

        skill_body = self.service.generate_skill_pr_body(
            skill_name="test",
            improvements="improvements",
            justification="justification",
            examples="examples",
        )

        # Agent PR should have agent-improver signature
        self.assertIn("agent-improver", agent_body)
        self.assertIn("Co-Authored-By", agent_body)

        # Skill PR should have skills-manager signature
        self.assertIn("skills-manager", skill_body)
        self.assertIn("Co-Authored-By", skill_body)


if __name__ == "__main__":
    unittest.main()
