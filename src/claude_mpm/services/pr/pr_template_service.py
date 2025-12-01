"""
Pull Request Template Service
==============================

Generates consistent PR titles and descriptions for agent/skill improvements.

Design Decisions:
- Follows conventional commit format
- Generates comprehensive PR descriptions with testing checklists
- Supports both agent and skill PR types
- Validates conventional commit message format

Example:
    >>> service = PRTemplateService()
    >>> title = service.generate_pr_title("research", "improve memory efficiency", PRType.AGENT)
    >>> print(title)
    feat(agent): improve research - improve memory efficiency

    >>> body = service.generate_agent_pr_body(
    ...     agent_name="research",
    ...     problem="Memory exhaustion with >50 files",
    ...     solution="Add hard limit of 5 files per session",
    ...     testing_notes="Tested with 100-file codebase",
    ...     related_issues=["#157"]
    ... )
"""

from enum import Enum
from typing import List, Optional


class PRType(Enum):
    """Type of pull request."""

    AGENT = "agent"
    SKILL = "skill"


class PRTemplateService:
    """
    Service for generating PR templates.

    Generates consistent PR titles and descriptions following
    conventional commit format and best practices.
    """

    # Conventional commit types
    COMMIT_TYPES = {
        "feat": "New feature or enhancement",
        "fix": "Bug fix",
        "docs": "Documentation changes",
        "refactor": "Code refactoring without feature changes",
        "test": "Adding or updating tests",
        "chore": "Maintenance tasks",
    }

    def generate_pr_title(
        self,
        item_name: str,
        brief_description: str,
        pr_type: PRType,
        commit_type: str = "feat",
    ) -> str:
        """
        Generate PR title in conventional commit format.

        Format: {commit_type}({scope}): {item} - {brief_description}

        Args:
            item_name: Agent or skill name (e.g., "research", "fastapi-testing")
            brief_description: Brief description (e.g., "improve memory handling")
            pr_type: Type of PR (agent or skill)
            commit_type: Conventional commit type (default: "feat")

        Returns:
            Formatted PR title

        Example:
            >>> service = PRTemplateService()
            >>> service.generate_pr_title("research", "improve memory handling", PRType.AGENT)
            'feat(agent): improve research - improve memory handling'
        """
        scope = pr_type.value
        return f"{commit_type}({scope}): improve {item_name} - {brief_description}"

    def generate_agent_pr_body(
        self,
        agent_name: str,
        problem: str,
        solution: str,
        testing_notes: str,
        related_issues: Optional[List[str]] = None,
    ) -> str:
        """
        Generate PR body for agent improvements.

        Args:
            agent_name: Agent name (e.g., "research")
            problem: Problem statement (what wasn't working)
            solution: Solution overview (what was changed)
            testing_notes: Testing performed
            related_issues: Related issue numbers (e.g., ["#157", "#142"])

        Returns:
            Formatted PR body in markdown

        Example:
            >>> service = PRTemplateService()
            >>> body = service.generate_agent_pr_body(
            ...     agent_name="research",
            ...     problem="Memory exhaustion when analyzing >50 files",
            ...     solution="Add hard limit of 5 files per session with MCP summarizer",
            ...     testing_notes="Tested with 100-file codebase, memory stayed under 4GB",
            ...     related_issues=["#157"]
            ... )
        """
        related_section = ""
        if related_issues:
            related_section = "\n\n## Related Issues\n\n"
            for issue in related_issues:
                # Check if it's just a number or already has #
                issue_ref = issue if issue.startswith("#") else f"#{issue}"
                related_section += f"Closes {issue_ref}\n"

        return f"""## Problem Statement

{problem}

## Proposed Solution

{solution}

## Changes Made

**Agent:** `{agent_name}`

{self._format_changes_placeholder()}

## Testing Performed

{testing_notes}

- [x] Validated YAML frontmatter syntax
- [x] Tested agent with sample tasks
- [x] Verified no regression in existing behavior
{related_section}
## Checklist

- [x] Instructions are clear and unambiguous
- [x] No conflicting guidance
- [x] Follows agent architecture best practices
- [x] Documentation updated if needed

---
🤖 Generated with Claude MPM Agent Improver
Co-Authored-By: agent-improver <noreply@anthropic.com>
"""

    def generate_skill_pr_body(
        self,
        skill_name: str,
        improvements: str,
        justification: str,
        examples: str,
        related_issues: Optional[List[str]] = None,
    ) -> str:
        """
        Generate PR body for skill improvements.

        Args:
            skill_name: Skill name (e.g., "fastapi-testing")
            improvements: Description of improvements made
            justification: Why these improvements were needed
            examples: Examples added or updated
            related_issues: Related issue numbers

        Returns:
            Formatted PR body in markdown

        Example:
            >>> service = PRTemplateService()
            >>> body = service.generate_skill_pr_body(
            ...     skill_name="fastapi-testing",
            ...     improvements="Added async test patterns and database handling",
            ...     justification="Users struggled with async endpoint testing",
            ...     examples="pytest-asyncio config, AsyncClient usage, DB rollback patterns",
            ...     related_issues=["#203"]
            ... )
        """
        related_section = ""
        if related_issues:
            related_section = "\n\n## Related Issues\n\n"
            for issue in related_issues:
                issue_ref = issue if issue.startswith("#") else f"#{issue}"
                related_section += f"Requested by: Issue {issue_ref}\n"

        return f"""## Skill Enhancement

**Skill:** `{skill_name}`

## Motivation

{justification}

## Improvements

{improvements}

## Examples Added

{examples}

## Testing

- [x] Validated YAML frontmatter
- [x] Verified skill syntax
- [x] Tested examples in relevant project
- [x] No conflicts with existing skills
{related_section}
---
🤖 Generated with Claude MPM Skills Manager
Co-Authored-By: skills-manager <noreply@anthropic.com>
"""

    def validate_conventional_commit(self, message: str) -> bool:
        """
        Validate that message follows conventional commit format.

        Format: type(scope): description

        Args:
            message: Commit message to validate

        Returns:
            True if message follows conventional commit format

        Example:
            >>> service = PRTemplateService()
            >>> service.validate_conventional_commit("feat(agent): improve research")
            True
            >>> service.validate_conventional_commit("improve research agent")
            False
        """
        if not message:
            return False

        # Extract first line (title)
        first_line = message.split("\n")[0]

        # Check basic format: type(scope): description
        if ":" not in first_line:
            return False

        # Split into type/scope and description
        parts = first_line.split(":", 1)
        if len(parts) != 2:
            return False

        type_scope = parts[0].strip()
        description = parts[1].strip()

        # Check type(scope) format
        if "(" not in type_scope or ")" not in type_scope:
            return False

        # Extract type
        commit_type = type_scope.split("(")[0].strip()

        # Validate type is recognized
        if commit_type not in self.COMMIT_TYPES:
            return False

        # Check description is not empty
        if not description:
            return False

        return True

    def _format_changes_placeholder(self) -> str:
        """
        Generate placeholder text for changes section.

        Returns:
            Formatted changes placeholder
        """
        return """_Detailed changes will be visible in the diff. Key modifications:_
- [List specific instruction changes]
- [List frontmatter updates if any]
- [List any related file changes]"""

    def generate_commit_message(
        self,
        item_name: str,
        brief_description: str,
        detailed_changes: str,
        pr_type: PRType,
        commit_type: str = "feat",
    ) -> str:
        """
        Generate conventional commit message.

        Args:
            item_name: Agent or skill name
            brief_description: Brief description
            detailed_changes: Detailed list of changes
            pr_type: Type (agent or skill)
            commit_type: Conventional commit type

        Returns:
            Formatted commit message

        Example:
            >>> service = PRTemplateService()
            >>> msg = service.generate_commit_message(
            ...     "research",
            ...     "improve memory efficiency",
            ...     "- Add hard limit of 5 files\\n- Document MCP summarizer",
            ...     PRType.AGENT
            ... )
        """
        scope = pr_type.value
        title = f"{commit_type}({scope}): improve {item_name} - {brief_description}"

        return f"""{title}

{detailed_changes}

🤖 Generated with Claude MPM
"""
