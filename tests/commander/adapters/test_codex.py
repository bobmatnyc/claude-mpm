"""Tests for Codex runtime adapter.

This module tests the CodexAdapter implementation, which provides
limited capabilities compared to other adapters.
"""

import pytest

from claude_mpm.commander.adapters import Capability, RuntimeCapability
from claude_mpm.commander.adapters.codex import CodexAdapter


class TestCodexAdapter:
    """Test suite for CodexAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a fresh adapter instance for each test."""
        return CodexAdapter()

    # Basic properties
    def test_name(self, adapter):
        """Test that adapter returns correct name."""
        assert adapter.name == "codex"

    def test_capabilities(self, adapter):
        """Test that adapter declares limited capabilities."""
        caps = adapter.capabilities
        assert isinstance(caps, set)

        # Codex has basic capabilities
        assert Capability.TOOL_USE in caps
        assert Capability.FILE_EDIT in caps
        assert Capability.FILE_CREATE in caps
        assert Capability.SHELL_COMMANDS in caps
        assert Capability.COMPLEX_REASONING in caps

        # Codex does NOT have advanced capabilities
        assert Capability.GIT_OPERATIONS not in caps
        assert Capability.WEB_SEARCH not in caps

    def test_runtime_info(self, adapter):
        """Test runtime_info provides correct information."""
        info = adapter.runtime_info

        assert info is not None
        assert info.name == "codex"
        assert info.command == "codex"
        assert info.supports_agents is False
        assert info.instruction_file is None  # No custom instructions support

        # Check runtime capabilities - limited set
        assert RuntimeCapability.FILE_READ in info.capabilities
        assert RuntimeCapability.FILE_EDIT in info.capabilities
        assert RuntimeCapability.FILE_CREATE in info.capabilities
        assert RuntimeCapability.BASH_EXECUTION in info.capabilities
        assert RuntimeCapability.TOOL_USE in info.capabilities

        # Should NOT have advanced features
        assert RuntimeCapability.AGENT_DELEGATION not in info.capabilities
        assert RuntimeCapability.HOOKS not in info.capabilities
        assert RuntimeCapability.SKILLS not in info.capabilities
        assert RuntimeCapability.MONITOR not in info.capabilities
        assert RuntimeCapability.MCP_TOOLS not in info.capabilities
        assert RuntimeCapability.INSTRUCTIONS not in info.capabilities
        assert RuntimeCapability.GIT_OPERATIONS not in info.capabilities

    # build_launch_command tests
    def test_build_launch_command_basic(self, adapter):
        """Test basic launch command."""
        cmd = adapter.build_launch_command("/home/user/project")
        assert "cd" in cmd
        assert "codex" in cmd

    def test_build_launch_command_with_agent_prompt(self, adapter, caplog):
        """Test that agent prompt triggers warning (not supported)."""
        import logging

        caplog.set_level(logging.WARNING)

        cmd = adapter.build_launch_command(
            "/home/user/project", "You are a Python expert"
        )

        # Command should still be built
        assert "codex" in cmd

        # Should log a warning
        assert any(
            "may not support custom prompts" in record.message
            for record in caplog.records
        )

    def test_build_launch_command_with_spaces(self, adapter):
        """Test launch command with path containing spaces."""
        path = "/home/user/My Workspace/app"
        cmd = adapter.build_launch_command(path)
        # Path should be quoted
        assert "'" in cmd or '"' in cmd
        assert "codex" in cmd

    # format_input tests
    def test_format_input_strips_whitespace(self, adapter):
        """Test that format_input strips whitespace."""
        result = adapter.format_input("  test  ")
        assert result == "test"

    # strip_ansi tests
    def test_strip_ansi_removes_codes(self, adapter):
        """Test that ANSI codes are removed."""
        text = "\x1b[31mRed\x1b[0m"
        result = adapter.strip_ansi(text)
        assert result == "Red"
        assert "\x1b" not in result

    # detect_idle tests
    def test_detect_idle_simple_prompt(self, adapter):
        """Test detecting simple prompt."""
        assert adapter.detect_idle("Done\n> ")

    def test_detect_idle_named_prompt(self, adapter):
        """Test detecting codex> prompt."""
        assert adapter.detect_idle("codex> ")

    def test_detect_idle_ready_message(self, adapter):
        """Test detecting 'Ready' message."""
        assert adapter.detect_idle("Ready")

    def test_detect_idle_waiting_message(self, adapter):
        """Test detecting 'Waiting for input' message."""
        assert adapter.detect_idle("Waiting for input")

    def test_detect_idle_not_idle(self, adapter):
        """Test that non-idle output is not detected."""
        assert not adapter.detect_idle("Working...")
        assert not adapter.detect_idle("")

    # detect_error tests
    def test_detect_error_basic(self, adapter):
        """Test detecting basic errors."""
        error = adapter.detect_error("Error: Command failed")
        assert error is not None
        assert "Error" in error

    def test_detect_error_failed(self, adapter):
        """Test detecting 'Failed:' prefix."""
        error = adapter.detect_error("Failed: Operation unsuccessful")
        assert error is not None

    def test_detect_error_traceback(self, adapter):
        """Test detecting traceback."""
        error = adapter.detect_error("Traceback:\n  File...")
        assert error is not None

    def test_detect_error_no_error(self, adapter):
        """Test that success messages don't trigger errors."""
        assert adapter.detect_error("Success") is None
        assert adapter.detect_error("Done") is None

    # detect_question tests
    def test_detect_question_yes_no(self, adapter):
        """Test detecting yes/no questions."""
        is_q, text, _options = adapter.detect_question("Proceed? (y/n)?")
        assert is_q is True
        assert text is not None

    def test_detect_question_with_options(self, adapter):
        """Test detecting questions with numbered options."""
        output = "Which option:\n1. Create\n2. Update"
        is_q, _text, options = adapter.detect_question(output)

        assert is_q is True
        assert options is not None
        assert len(options) == 2

    def test_detect_question_no_question(self, adapter):
        """Test that non-questions are not detected."""
        is_q, _text, _options = adapter.detect_question("Operation complete")
        assert is_q is False

    # parse_response tests
    def test_parse_response_success(self, adapter):
        """Test parsing successful response."""
        response = adapter.parse_response("Completed\n> ")
        assert response.is_complete is True
        assert response.is_error is False

    def test_parse_response_error(self, adapter):
        """Test parsing error response."""
        response = adapter.parse_response("Error: Invalid\n> ")
        assert response.is_error is True
        assert response.error_message is not None

    def test_parse_response_empty(self, adapter):
        """Test parsing empty output."""
        response = adapter.parse_response("")
        assert response.content == ""
        assert response.is_complete is False

    def test_parse_response_incomplete(self, adapter):
        """Test parsing incomplete response."""
        response = adapter.parse_response("Loading...")
        assert response.is_complete is False

    # No instruction injection support
    def test_inject_instructions_not_supported(self, adapter):
        """Test that inject_instructions returns None (not supported)."""
        result = adapter.inject_instructions("Test instructions")
        assert result is None

    def test_inject_agent_context_not_supported(self, adapter):
        """Test that inject_agent_context returns None (not supported)."""
        result = adapter.inject_agent_context("agent-001", {"role": "test"})
        assert result is None
