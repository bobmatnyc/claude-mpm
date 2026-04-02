"""Tests for initialPrompt frontmatter support (issue #418).

Tests the get_initial_prompt function and verifies that the template builder
correctly injects initialPrompt into agent frontmatter.
"""

import pytest

from claude_mpm.services.agents.deployment.agent_template_builder import (
    INITIAL_PROMPT_BY_NAME,
    INITIAL_PROMPT_BY_TYPE,
    INITIAL_PROMPT_EXCLUDED_NAMES,
    get_initial_prompt,
)


class TestGetInitialPrompt:
    """Tests for the get_initial_prompt function."""

    def test_research_agent_by_name(self):
        result = get_initial_prompt("research", "research")
        assert result is not None
        assert "investigation" in result.lower()

    def test_documentation_agent_by_name(self):
        result = get_initial_prompt("documentation", "documentation")
        assert result is not None
        assert "documentation" in result.lower()

    def test_security_agent_by_name(self):
        result = get_initial_prompt("security", "security")
        assert result is not None
        assert "security" in result.lower()

    def test_engineer_agent_by_type(self):
        result = get_initial_prompt("python-engineer", "engineer")
        assert result is not None
        assert "implementation" in result.lower()

    def test_qa_agent_by_type(self):
        result = get_initial_prompt("qa", "qa")
        assert result is not None
        assert "verification" in result.lower()

    def test_web_qa_agent_by_type(self):
        result = get_initial_prompt("web-qa", "qa")
        assert result is not None
        assert "verification" in result.lower()

    def test_api_qa_agent_by_type(self):
        result = get_initial_prompt("api-qa", "qa")
        assert result is not None
        assert "verification" in result.lower()

    def test_ops_agent_by_type(self):
        result = get_initial_prompt("ops", "ops")
        assert result is not None
        assert "operations" in result.lower()

    def test_local_ops_agent_by_type(self):
        result = get_initial_prompt("local-ops", "ops")
        assert result is not None
        assert "operations" in result.lower()

    def test_all_language_engineers_get_implementation_prompt(self):
        """All language-specific engineers should get the engineer type prompt."""
        engineers = [
            "python-engineer",
            "typescript-engineer",
            "javascript-engineer",
            "golang-engineer",
            "java-engineer",
            "ruby-engineer",
            "rust-engineer",
            "php-engineer",
            "phoenix-engineer",
            "dart-engineer",
            "react-engineer",
            "nextjs-engineer",
            "svelte-engineer",
            "tauri-engineer",
            "data-engineer",
        ]
        for name in engineers:
            result = get_initial_prompt(name, "engineer")
            assert result is not None, f"{name} should have an initialPrompt"
            assert "implementation" in result.lower(), (
                f"{name} should mention implementation"
            )

    def test_refactoring_engineer_by_type(self):
        result = get_initial_prompt("refactoring-engineer", "refactoring")
        assert result is not None
        assert "implementation" in result.lower()


class TestExcludedAgents:
    """Test that excluded agents do not get initialPrompt."""

    def test_prompt_engineer_excluded(self):
        result = get_initial_prompt("prompt-engineer", "analysis")
        assert result is None

    def test_real_user_excluded(self):
        result = get_initial_prompt("real-user", "qa")
        assert result is None

    def test_memory_manager_excluded(self):
        result = get_initial_prompt("memory-manager", "memory_manager")
        assert result is None

    def test_memory_manager_agent_excluded(self):
        result = get_initial_prompt("memory-manager-agent", "memory_manager")
        assert result is None

    def test_ticketing_excluded(self):
        result = get_initial_prompt("ticketing", None)
        assert result is None

    def test_mpm_agent_manager_excluded(self):
        result = get_initial_prompt("mpm-agent-manager", None)
        assert result is None


class TestNamePrecedenceOverType:
    """Test that name-based lookup takes precedence over type-based."""

    def test_research_name_takes_precedence(self):
        """Research has both name and type mappings; name should win."""
        name_result = INITIAL_PROMPT_BY_NAME.get("research")
        type_result = INITIAL_PROMPT_BY_TYPE.get("research")
        # Both should exist
        assert name_result is not None
        assert type_result is not None
        # get_initial_prompt should return the name-based one
        result = get_initial_prompt("research", "research")
        assert result == name_result


class TestUnknownAgents:
    """Test behavior for unknown agent names/types."""

    def test_unknown_name_and_type_returns_none(self):
        result = get_initial_prompt("unknown-agent", "unknown-type")
        assert result is None

    def test_unknown_name_with_known_type(self):
        result = get_initial_prompt("custom-engineer", "engineer")
        assert result is not None
        assert "implementation" in result.lower()

    def test_known_name_with_none_type(self):
        result = get_initial_prompt("research", None)
        assert result is not None

    def test_none_type_unknown_name(self):
        result = get_initial_prompt("completely-unknown", None)
        assert result is None


class TestInitialPromptMappingConsistency:
    """Verify that the mapping constants are well-formed."""

    def test_all_name_prompts_are_nonempty_strings(self):
        for name, prompt in INITIAL_PROMPT_BY_NAME.items():
            assert isinstance(prompt, str), f"{name} prompt must be string"
            assert len(prompt) > 10, f"{name} prompt too short"

    def test_all_type_prompts_are_nonempty_strings(self):
        for agent_type, prompt in INITIAL_PROMPT_BY_TYPE.items():
            assert isinstance(prompt, str), f"{agent_type} prompt must be string"
            assert len(prompt) > 10, f"{agent_type} prompt too short"

    def test_excluded_names_are_strings(self):
        for name in INITIAL_PROMPT_EXCLUDED_NAMES:
            assert isinstance(name, str), f"Excluded name must be string: {name}"
            assert len(name) > 0, "Excluded name must not be empty"

    def test_no_overlap_between_excluded_and_name_map(self):
        """Excluded names should not appear in the name-based map."""
        overlap = INITIAL_PROMPT_EXCLUDED_NAMES & set(INITIAL_PROMPT_BY_NAME.keys())
        assert not overlap, f"Names in both excluded and map: {overlap}"
