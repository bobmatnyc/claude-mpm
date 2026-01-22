"""Tests for Auggie runtime adapter.

This module tests the AuggieAdapter implementation, including
MCP support and custom instruction injection.
"""

import pytest

from claude_mpm.commander.adapters import Capability, RuntimeCapability
from claude_mpm.commander.adapters.auggie import AuggieAdapter


class TestAuggieAdapter:
    """Test suite for AuggieAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a fresh adapter instance for each test."""
        return AuggieAdapter()

    # Basic properties
    def test_name(self, adapter):
        """Test that adapter returns correct name."""
        assert adapter.name == "auggie"

    def test_capabilities(self, adapter):
        """Test that adapter declares expected capabilities."""
        caps = adapter.capabilities
        assert isinstance(caps, set)
        assert Capability.TOOL_USE in caps
        assert Capability.FILE_EDIT in caps
        assert Capability.FILE_CREATE in caps
        assert Capability.GIT_OPERATIONS in caps
        assert Capability.SHELL_COMMANDS in caps
        assert Capability.COMPLEX_REASONING in caps

        # Auggie doesn't have web search (unlike Claude Code)
        assert Capability.WEB_SEARCH not in caps

    def test_runtime_info(self, adapter):
        """Test runtime_info provides correct information."""
        info = adapter.runtime_info

        assert info is not None
        assert info.name == "auggie"
        assert info.command == "auggie"
        assert info.supports_agents is True
        assert info.instruction_file == ".augment/instructions.md"

        # Check runtime capabilities - Auggie has MCP support
        assert RuntimeCapability.MCP_TOOLS in info.capabilities
        assert RuntimeCapability.INSTRUCTIONS in info.capabilities
        assert RuntimeCapability.FILE_EDIT in info.capabilities
        assert RuntimeCapability.TOOL_USE in info.capabilities

        # Should now have AGENT_DELEGATION
        assert RuntimeCapability.AGENT_DELEGATION in info.capabilities

        # Should NOT have Claude Code-specific features
        assert RuntimeCapability.HOOKS not in info.capabilities
        assert RuntimeCapability.SKILLS not in info.capabilities
        assert RuntimeCapability.MONITOR not in info.capabilities

    # build_launch_command tests
    def test_build_launch_command_basic(self, adapter):
        """Test basic launch command without agent prompt."""
        cmd = adapter.build_launch_command("/home/user/project")
        assert "cd" in cmd
        assert "auggie" in cmd

    def test_build_launch_command_with_agent_prompt(self, adapter):
        """Test launch command with agent prompt."""
        cmd = adapter.build_launch_command(
            "/home/user/project", "You are a Python expert"
        )
        assert "auggie" in cmd
        assert "--prompt" in cmd
        assert "Python expert" in cmd

    def test_build_launch_command_with_spaces(self, adapter):
        """Test launch command with path containing spaces."""
        path = "/home/user/My Projects/app"
        cmd = adapter.build_launch_command(path)
        # Path should be quoted
        assert "'" in cmd or '"' in cmd
        assert "auggie" in cmd

    # format_input tests
    def test_format_input_strips_whitespace(self, adapter):
        """Test that format_input strips whitespace."""
        result = adapter.format_input("  test  ")
        assert result == "test"

    # strip_ansi tests
    def test_strip_ansi_removes_codes(self, adapter):
        """Test that ANSI codes are removed."""
        text = "\x1b[32mGreen\x1b[0m"
        result = adapter.strip_ansi(text)
        assert result == "Green"
        assert "\x1b" not in result

    # detect_idle tests
    def test_detect_idle_simple_prompt(self, adapter):
        """Test detecting simple prompt."""
        assert adapter.detect_idle("Done\n> ")

    def test_detect_idle_named_prompt(self, adapter):
        """Test detecting auggie> prompt."""
        assert adapter.detect_idle("auggie> ")

    def test_detect_idle_ready_message(self, adapter):
        """Test detecting 'Ready for input' message."""
        assert adapter.detect_idle("Ready for input")

    def test_detect_idle_greeting(self, adapter):
        """Test detecting greeting messages."""
        assert adapter.detect_idle("What would you like to do?")
        assert adapter.detect_idle("How can I assist you today?")

    def test_detect_idle_not_idle(self, adapter):
        """Test that non-idle output is not detected."""
        assert not adapter.detect_idle("Processing...")
        assert not adapter.detect_idle("")

    # detect_error tests
    def test_detect_error_basic(self, adapter):
        """Test detecting basic errors."""
        error = adapter.detect_error("Error: Something failed")
        assert error is not None
        assert "Error" in error

    def test_detect_error_permission_denied(self, adapter):
        """Test detecting permission errors."""
        error = adapter.detect_error("Permission denied: /root")
        assert error is not None

    def test_detect_error_no_error(self, adapter):
        """Test that success messages don't trigger errors."""
        assert adapter.detect_error("Success!") is None
        assert adapter.detect_error("Completed") is None

    # detect_question tests
    def test_detect_question_yes_no(self, adapter):
        """Test detecting yes/no questions."""
        is_q, text, _options = adapter.detect_question("Continue? (y/n)?")
        assert is_q is True
        assert text is not None

    def test_detect_question_with_options(self, adapter):
        """Test detecting questions with numbered options."""
        output = "Which option:\n1. First option\n2. Second option"
        is_q, _text, options = adapter.detect_question(output)

        assert is_q is True
        assert options is not None
        assert len(options) == 2

    def test_detect_question_no_question(self, adapter):
        """Test that non-questions are not detected."""
        is_q, _text, _options = adapter.detect_question("Task completed")
        assert is_q is False

    # parse_response tests
    def test_parse_response_success(self, adapter):
        """Test parsing successful response."""
        response = adapter.parse_response("Task done\n> ")
        assert response.is_complete is True
        assert response.is_error is False

    def test_parse_response_error(self, adapter):
        """Test parsing error response."""
        response = adapter.parse_response("Error: Failed\n> ")
        assert response.is_error is True
        assert response.error_message is not None

    def test_parse_response_empty(self, adapter):
        """Test parsing empty output."""
        response = adapter.parse_response("")
        assert response.content == ""
        assert response.is_complete is False

    # inject_instructions tests
    def test_inject_instructions(self, adapter):
        """Test injecting custom instructions."""
        instructions = "You are a Python expert"
        cmd = adapter.inject_instructions(instructions)

        assert cmd is not None
        assert ".augment/instructions.md" in cmd
        assert "mkdir -p .augment" in cmd
        assert "echo" in cmd
        assert "Python expert" in cmd

    def test_inject_instructions_with_quotes(self, adapter):
        """Test injecting instructions with quotes (should be escaped)."""
        instructions = "You're an expert"
        cmd = adapter.inject_instructions(instructions)

        assert cmd is not None
        # The single quote should be escaped
        assert ".augment/instructions.md" in cmd

    def test_inject_instructions_multiline(self, adapter):
        """Test injecting multiline instructions."""
        instructions = "Line 1\nLine 2\nLine 3"
        cmd = adapter.inject_instructions(instructions)

        assert cmd is not None
        assert ".augment/instructions.md" in cmd
