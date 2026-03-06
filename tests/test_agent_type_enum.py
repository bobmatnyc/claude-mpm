"""Test AgentType enum extension and from_frontmatter parsing."""

import pytest

from claude_mpm.models.agent_definition import AgentType


class TestAgentTypeEnum:
    """Verify AgentType enum covers all frontmatter values."""

    def test_original_values_preserved(self):
        """Original enum values must not change."""
        assert AgentType.CORE.value == "core"
        assert AgentType.PROJECT.value == "project"
        assert AgentType.CUSTOM.value == "custom"
        assert AgentType.SYSTEM.value == "system"
        assert AgentType.SPECIALIZED.value == "specialized"

    def test_new_role_categories(self):
        """New role categories exist."""
        assert AgentType.ENGINEER.value == "engineer"
        assert AgentType.QA.value == "qa"
        assert AgentType.OPS.value == "ops"
        assert AgentType.RESEARCH.value == "research"
        assert AgentType.SECURITY.value == "security"
        assert AgentType.DOCUMENTATION.value == "documentation"
        assert AgentType.VERSION_CONTROL.value == "version_control"
        assert AgentType.DATA.value == "data"
        assert AgentType.CONTENT.value == "content"
        assert AgentType.MANAGEMENT.value == "management"

    def test_from_frontmatter_exact_match(self):
        """Exact string values map correctly."""
        assert AgentType.from_frontmatter("engineer") == AgentType.ENGINEER
        assert AgentType.from_frontmatter("core") == AgentType.CORE
        assert AgentType.from_frontmatter("qa") == AgentType.QA

    def test_from_frontmatter_aliases(self):
        """Common aliases map correctly."""
        assert AgentType.from_frontmatter("core_agent") == AgentType.CORE
        assert AgentType.from_frontmatter("engineer_agent") == AgentType.ENGINEER
        assert AgentType.from_frontmatter("code_analysis") == AgentType.RESEARCH

    def test_from_frontmatter_unknown(self):
        """Unknown values fall back to CUSTOM."""
        assert AgentType.from_frontmatter("totally_unknown") == AgentType.CUSTOM
        assert AgentType.from_frontmatter("") == AgentType.CUSTOM
        assert AgentType.from_frontmatter(None) == AgentType.CUSTOM

    def test_from_frontmatter_normalization(self):
        """Input is normalized before matching."""
        assert AgentType.from_frontmatter("  Engineer  ") == AgentType.ENGINEER
        assert (
            AgentType.from_frontmatter("version-control") == AgentType.VERSION_CONTROL
        )
        assert (
            AgentType.from_frontmatter("Version_Control") == AgentType.VERSION_CONTROL
        )
