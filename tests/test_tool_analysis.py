"""Tests for tool_analysis.extract_tool_parameters."""

import pytest

from claude_mpm.hooks.claude_hooks.tool_analysis import extract_tool_parameters


class TestExtractToolParametersTask:
    """Test Task tool parameter extraction with agent normalization."""

    @pytest.mark.parametrize(
        "subagent_type,expected_pm,expected_research,expected_engineer",
        [
            # Exact lowercase matches (existing behavior)
            ("pm", True, False, False),
            ("research", False, True, False),
            ("engineer", False, False, True),
            # Case-insensitive (new behavior from normalization)
            ("PM", True, False, False),
            ("Research", False, True, False),
            ("Engineer", False, False, True),
            # With -agent suffix (normalize_agent_id strips it)
            ("research-agent", False, True, False),
            ("pm-agent", True, False, False),
            # Compound agents (should NOT match simple flags)
            ("python-engineer", False, False, False),
            ("rust-engineer", False, False, False),
            # Display-name form with "Agent" suffix (should match after stripping)
            ("Engineer Agent", False, False, True),
            ("Research Agent", False, True, False),
            ("PM Agent", True, False, False),
            # Unknown agents
            ("qa", False, False, False),
            ("documentation", False, False, False),
            ("unknown", False, False, False),
        ],
    )
    def test_task_delegation_flags(
        self, subagent_type, expected_pm, expected_research, expected_engineer
    ):
        result = extract_tool_parameters("Task", {"subagent_type": subagent_type})
        assert result["is_pm_delegation"] == expected_pm, (
            f"is_pm_delegation for '{subagent_type}'"
        )
        assert result["is_research_delegation"] == expected_research, (
            f"is_research_delegation for '{subagent_type}'"
        )
        assert result["is_engineer_delegation"] == expected_engineer, (
            f"is_engineer_delegation for '{subagent_type}'"
        )

    def test_raw_subagent_type_preserved(self):
        """The subagent_type in output should be the raw value, not normalized."""
        result = extract_tool_parameters("Task", {"subagent_type": "Research Agent"})
        assert result["subagent_type"] == "Research Agent"
        assert result["is_research_delegation"] is True

    def test_missing_subagent_type(self):
        """Missing subagent_type should default to 'unknown' and all flags False."""
        result = extract_tool_parameters("Task", {})
        assert result["subagent_type"] == "unknown"
        assert result["is_pm_delegation"] is False
        assert result["is_research_delegation"] is False
        assert result["is_engineer_delegation"] is False

    def test_none_subagent_type(self):
        """None subagent_type should not crash."""
        result = extract_tool_parameters("Task", {"subagent_type": None})
        assert result["is_pm_delegation"] is False
        assert result["is_research_delegation"] is False
        assert result["is_engineer_delegation"] is False


class TestExtractToolParametersOtherTools:
    """Verify other tool types still work correctly."""

    def test_bash_tool(self):
        result = extract_tool_parameters(
            "Bash", {"command": "echo hello", "timeout": 5000}
        )
        assert result["command"] == "echo hello"
        assert result["has_pipe"] is False

    def test_write_tool(self):
        result = extract_tool_parameters(
            "Write", {"file_path": "/tmp/test.py", "content": "x = 1"}
        )
        assert result["file_path"] == "/tmp/test.py"
        assert result["is_create"] is True

    def test_non_dict_input(self):
        result = extract_tool_parameters("Unknown", "some string")
        assert "raw_input" in result
