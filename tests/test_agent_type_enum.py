"""Test AgentType alias and backward compatibility."""

import pytest

from claude_mpm.models.agent_definition import AgentRole, AgentType


class TestAgentTypeAlias:
    """Verify AgentType is an alias for AgentRole."""

    def test_alias_identity(self):
        """AgentType IS AgentRole."""
        assert AgentType is AgentRole

    def test_role_values_accessible(self):
        """Role values work through the alias."""
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
        assert AgentType.SPECIALIZED.value == "specialized"
        assert AgentType.OTHER.value == "other"

    def test_source_values_removed(self):
        """Source-only values no longer exist."""
        assert not hasattr(AgentType, "CORE")
        assert not hasattr(AgentType, "PROJECT")
        assert not hasattr(AgentType, "CUSTOM")
        assert not hasattr(AgentType, "SYSTEM")

    def test_from_frontmatter_works(self):
        """from_frontmatter works through alias."""
        assert AgentType.from_frontmatter("engineer") == AgentRole.ENGINEER
        assert AgentType.from_frontmatter("qa") == AgentRole.QA
        assert AgentType.from_frontmatter("core") == AgentRole.OTHER
        assert AgentType.from_frontmatter(None) == AgentRole.OTHER

    def test_from_frontmatter_normalization(self):
        """Normalization works through alias."""
        assert AgentType.from_frontmatter("  Engineer  ") == AgentRole.ENGINEER
        assert (
            AgentType.from_frontmatter("version-control") == AgentRole.VERSION_CONTROL
        )

    def test_unknown_falls_to_other(self):
        """Unknown values return OTHER (not CUSTOM)."""
        assert AgentType.from_frontmatter("totally_unknown") == AgentRole.OTHER
        assert AgentType.from_frontmatter("") == AgentRole.OTHER
