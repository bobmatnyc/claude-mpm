"""Tests for the AgentRole enum."""

import pytest

from claude_mpm.core.unified_agent_registry import AgentSourceType
from claude_mpm.models.agent_definition import AgentMetadata, AgentRole


class TestAgentRoleMembers:
    """Verify all expected members exist with correct values."""

    @pytest.mark.parametrize(
        "member,value",
        [
            ("ENGINEER", "engineer"),
            ("QA", "qa"),
            ("OPS", "ops"),
            ("RESEARCH", "research"),
            ("SECURITY", "security"),
            ("DOCUMENTATION", "documentation"),
            ("VERSION_CONTROL", "version_control"),
            ("DATA", "data"),
            ("CONTENT", "content"),
            ("MANAGEMENT", "management"),
            ("SPECIALIZED", "specialized"),
            ("OTHER", "other"),
        ],
    )
    def test_member_exists(self, member, value):
        assert getattr(AgentRole, member).value == value

    def test_member_count(self):
        assert len(AgentRole) == 12


class TestFromFrontmatter:
    """Verify frontmatter parsing."""

    # Direct role matches
    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("engineer", AgentRole.ENGINEER),
            ("qa", AgentRole.QA),
            ("ops", AgentRole.OPS),
            ("research", AgentRole.RESEARCH),
            ("documentation", AgentRole.DOCUMENTATION),
            ("security", AgentRole.SECURITY),
            ("content", AgentRole.CONTENT),
            ("management", AgentRole.MANAGEMENT),
            ("specialized", AgentRole.SPECIALIZED),
        ],
    )
    def test_direct_role_match(self, input_val, expected):
        assert AgentRole.from_frontmatter(input_val) == expected

    # Source values -> OTHER
    @pytest.mark.parametrize(
        "input_val",
        [
            "core",
            "project",
            "custom",
            "system",
        ],
    )
    def test_source_values_map_to_other(self, input_val):
        assert AgentRole.from_frontmatter(input_val) == AgentRole.OTHER

    # Aliases
    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("product", AgentRole.MANAGEMENT),
            ("refactoring", AgentRole.ENGINEER),
            ("analysis", AgentRole.RESEARCH),
            ("code_analysis", AgentRole.RESEARCH),
            ("memory_manager", AgentRole.MANAGEMENT),
            ("imagemagick", AgentRole.SPECIALIZED),
            ("image_processing", AgentRole.SPECIALIZED),
            ("claude_mpm", AgentRole.OTHER),
            ("product_management", AgentRole.MANAGEMENT),
            ("prompt_engineering", AgentRole.ENGINEER),
        ],
    )
    def test_aliases(self, input_val, expected):
        assert AgentRole.from_frontmatter(input_val) == expected

    # Normalization
    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("ENGINEER", AgentRole.ENGINEER),
            ("Engineer", AgentRole.ENGINEER),
            ("code-analysis", AgentRole.RESEARCH),
            ("claude-mpm", AgentRole.OTHER),
            ("  engineer  ", AgentRole.ENGINEER),
        ],
    )
    def test_normalization(self, input_val, expected):
        assert AgentRole.from_frontmatter(input_val) == expected

    # Edge cases
    def test_none_returns_other(self):
        assert AgentRole.from_frontmatter(None) == AgentRole.OTHER

    def test_empty_string_returns_other(self):
        assert AgentRole.from_frontmatter("") == AgentRole.OTHER

    def test_unknown_value_returns_other(self):
        assert AgentRole.from_frontmatter("xyzzy") == AgentRole.OTHER

    # Pipe-delimited
    def test_pipe_delimited_takes_first(self):
        result = AgentRole.from_frontmatter("engineer|qa|ops|universal|documentation")
        assert result == AgentRole.ENGINEER

    def test_pipe_delimited_first_unknown(self):
        result = AgentRole.from_frontmatter("universal|engineer")
        assert result == AgentRole.OTHER  # "universal" is unknown


class TestAgentMetadataFields:
    """Verify AgentMetadata role and source fields."""

    def test_role_field_required(self):
        m = AgentMetadata(role=AgentRole.ENGINEER)
        assert m.role == AgentRole.ENGINEER

    def test_type_property_returns_role(self):
        m = AgentMetadata(role=AgentRole.ENGINEER)
        assert m.type == AgentRole.ENGINEER

    def test_source_defaults_to_none(self):
        m = AgentMetadata(role=AgentRole.ENGINEER)
        assert m.source is None

    def test_explicit_source_preserved(self):
        m = AgentMetadata(
            role=AgentRole.ENGINEER,
            source=AgentSourceType.CORE,
        )
        assert m.source == AgentSourceType.CORE
        assert m.role == AgentRole.ENGINEER

    def test_role_other(self):
        m = AgentMetadata(role=AgentRole.OTHER)
        assert m.role == AgentRole.OTHER

    def test_role_qa(self):
        m = AgentMetadata(role=AgentRole.QA)
        assert m.role == AgentRole.QA

    def test_role_ops(self):
        m = AgentMetadata(role=AgentRole.OPS)
        assert m.role == AgentRole.OPS

    def test_type_property_matches_role(self):
        m = AgentMetadata(role=AgentRole.SPECIALIZED)
        assert m.type == m.role
