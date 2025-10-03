"""
Content validation for framework CLAUDE.md templates.

Validates generated content structure and completeness.
"""

import re
from typing import ClassVar, List, Tuple


class ContentValidator:
    """Validates framework CLAUDE.md content for completeness and correctness."""

    # Required sections that must be present
    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        (r"CLAUDE_MD_VERSION:", "Version metadata"),
        (r"## 🤖 AI ASSISTANT ROLE DESIGNATION", "Role designation section"),
        (r"## A\) AGENTS", "Agents section"),
        (r"## B\) TODO AND TASK TOOLS", "Todo/Task tools section"),
        (r"## C\) CLAUDE-PM INIT", "Claude-PM init section"),
        (r"## 🚨 CORE ORCHESTRATION PRINCIPLES", "Orchestration principles"),
        (r"## 🔥🚨 CRITICAL: SUBPROCESS VALIDATION PROTOCOL", "Subprocess validation"),
        (r"## 🚨 CRITICAL DELEGATION CONSTRAINTS", "Delegation constraints"),
        (r"## 🚨 TROUBLESHOOTING", "Troubleshooting section"),
        (r"## Core Responsibilities", "Core responsibilities"),
    ]

    # Template variables that are allowed to remain unsubstituted for runtime
    ALLOWED_RUNTIME_VARS = {
        "{{DEPLOYMENT_ID}}",
        "{{PLATFORM}}",
        "{{PYTHON_CMD}}",
        "{{PLATFORM_NOTES}}",
    }

    def validate_content(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate that generated content has all required sections.

        Args:
            content: Content to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check for required sections
        for pattern, section_name in self.REQUIRED_SECTIONS:
            if not re.search(pattern, content):
                issues.append(f"Missing required section: {section_name}")

        # Check for unsubstituted template variables
        unsubstituted = re.findall(r"\{\{[^}]+\}\}", content)
        unexpected_vars = [
            var for var in unsubstituted if var not in self.ALLOWED_RUNTIME_VARS
        ]
        if unexpected_vars:
            issues.append(
                f"Unsubstituted template variables: {', '.join(set(unexpected_vars))}"
            )

        # Validate version format - now accepts simple serial numbers
        version_match = re.search(r"CLAUDE_MD_VERSION:\s*(\d+)(?:-(\d+))?", content)
        if not version_match:
            issues.append("Invalid or missing CLAUDE_MD_VERSION format")

        # Check for proper structure
        if not content.strip():
            issues.append("Content is empty")

        # Validate agent section completeness
        if "## A) AGENTS" in content:
            required_agents = [
                "Documentation Agent",
                "Ticketing Agent",
                "Version Control Agent",
                "QA Agent",
                "Research Agent",
                "Ops Agent",
                "Security Agent",
                "Engineer Agent",
                "Data Engineer Agent",
            ]
            for agent in required_agents:
                if agent not in content:
                    issues.append(f"Missing core agent: {agent}")

        return len(issues) == 0, issues

    def validate_section_order(self, sections: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that sections are in the correct order.

        Args:
            sections: List of section names in order

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        expected_order = [
            "header",
            "role_designation",
            "agents",
            "todo_task_tools",
            "claude_pm_init",
            "orchestration_principles",
            "subprocess_validation",
            "delegation_constraints",
            "environment_config",
            "troubleshooting",
            "core_responsibilities",
            "footer",
        ]

        issues = []

        # Check that all expected sections are present
        missing = set(expected_order) - set(sections)
        if missing:
            issues.append(f"Missing sections: {', '.join(missing)}")

        # Check order (only for sections that exist in both lists)
        common_sections = [s for s in sections if s in expected_order]
        expected_common = [s for s in expected_order if s in sections]

        if common_sections != expected_common:
            issues.append("Sections are not in the expected order")

        return len(issues) == 0, issues
