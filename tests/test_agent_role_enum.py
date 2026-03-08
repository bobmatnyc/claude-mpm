"""Tests for the AgentRole enum."""

import pytest

from claude_mpm.core.unified_agent_registry import AgentSourceType
from claude_mpm.models.agent_definition import AgentMetadata, AgentRole, AgentType


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


class TestAgentMetadataDualFields:
    """Verify dual-field population on AgentMetadata."""

    def test_auto_populate_role_from_type_engineer(self):
        m = AgentMetadata(type=AgentType.ENGINEER)
        assert m.role == AgentRole.ENGINEER

    def test_auto_populate_role_from_type_core(self):
        m = AgentMetadata(type=AgentType.CORE)
        assert m.role == AgentRole.OTHER  # Source value -> OTHER

    def test_explicit_role_not_overwritten(self):
        m = AgentMetadata(type=AgentType.CORE, role=AgentRole.ENGINEER)
        assert m.role == AgentRole.ENGINEER

    def test_source_defaults_to_none(self):
        m = AgentMetadata(type=AgentType.ENGINEER)
        assert m.source is None

    def test_explicit_source_preserved(self):
        m = AgentMetadata(
            type=AgentType.ENGINEER,
            source=AgentSourceType.CORE,
        )
        assert m.source == AgentSourceType.CORE
        assert m.role == AgentRole.ENGINEER

    def test_auto_populate_role_from_type_qa(self):
        m = AgentMetadata(type=AgentType.QA)
        assert m.role == AgentRole.QA

    def test_auto_populate_role_from_type_ops(self):
        m = AgentMetadata(type=AgentType.OPS)
        assert m.role == AgentRole.OPS

    def test_auto_populate_role_from_type_custom(self):
        m = AgentMetadata(type=AgentType.CUSTOM)
        assert m.role == AgentRole.OTHER  # "custom" is not in AgentRole
