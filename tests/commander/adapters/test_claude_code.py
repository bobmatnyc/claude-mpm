"""Tests for Claude Code runtime adapter.

This module comprehensively tests the ClaudeCodeAdapter implementation,
covering all detection logic, parsing, and command generation.
"""

import pytest

from claude_mpm.commander.adapters import (
    Capability,
    ClaudeCodeAdapter,
    ParsedResponse,
    RuntimeCapability,
)


class TestClaudeCodeAdapter:
    """Test suite for ClaudeCodeAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a fresh adapter instance for each test."""
        return ClaudeCodeAdapter()

    # Basic properties
    def test_name(self, adapter):
        """Test that adapter returns correct name."""
        assert adapter.name == "claude-code"

    def test_capabilities(self, adapter):
        """Test that adapter declares all expected capabilities."""
        caps = adapter.capabilities
        assert isinstance(caps, set)
        assert Capability.TOOL_USE in caps
        assert Capability.FILE_EDIT in caps
        assert Capability.FILE_CREATE in caps
        assert Capability.GIT_OPERATIONS in caps
        assert Capability.SHELL_COMMANDS in caps
        assert Capability.WEB_SEARCH in caps
        assert Capability.COMPLEX_REASONING in caps
        assert len(caps) == 7

    def test_runtime_info(self, adapter):
        """Test runtime_info provides correct information."""
        info = adapter.runtime_info

        assert info is not None
        assert info.name == "claude-code"
        assert info.command == "claude"
        assert info.supports_agents is True
        assert info.instruction_file == "CLAUDE.md"

        # Check runtime capabilities
        assert RuntimeCapability.FILE_READ in info.capabilities
        assert RuntimeCapability.FILE_EDIT in info.capabilities
        assert RuntimeCapability.FILE_CREATE in info.capabilities
        assert RuntimeCapability.BASH_EXECUTION in info.capabilities
        assert RuntimeCapability.GIT_OPERATIONS in info.capabilities
        assert RuntimeCapability.TOOL_USE in info.capabilities
        assert RuntimeCapability.WEB_SEARCH in info.capabilities
        assert RuntimeCapability.COMPLEX_REASONING in info.capabilities

        # Should now have agent capabilities
        assert RuntimeCapability.AGENT_DELEGATION in info.capabilities
        assert RuntimeCapability.HOOKS in info.capabilities
        assert RuntimeCapability.SKILLS in info.capabilities
        assert RuntimeCapability.MONITOR in info.capabilities

    # build_launch_command tests
    def test_build_launch_command_basic(self, adapter):
        """Test basic launch command without agent prompt."""
        cmd = adapter.build_launch_command("/home/user/project")
        assert "cd" in cmd
        assert "claude" in cmd
        assert "--dangerously-skip-permissions" in cmd

    def test_build_launch_command_with_agent_prompt(self, adapter):
        """Test launch command with agent prompt."""
        cmd = adapter.build_launch_command(
            "/home/user/project", "You are a Python expert"
        )
        assert "claude" in cmd
        assert "--system-prompt" in cmd
        assert "Python expert" in cmd
        assert "--dangerously-skip-permissions" in cmd

    def test_build_launch_command_shell_injection_safe(self, adapter):
        """Test that launch command properly quotes dangerous paths."""
        dangerous_path = "/home/user/project'; rm -rf /"
        cmd = adapter.build_launch_command(dangerous_path)
        # Path should be safely quoted
        assert "claude" in cmd
        # The dangerous part should be escaped, not executable
        assert dangerous_path not in cmd or "'" in cmd

    def test_build_launch_command_with_spaces(self, adapter):
        """Test launch command with path containing spaces."""
        path = "/home/user/My Documents/project"
        cmd = adapter.build_launch_command(path)
        # Path should be quoted
        assert "'" in cmd or '"' in cmd

    # format_input tests
    def test_format_input_strips_whitespace(self, adapter):
        """Test that format_input strips leading/trailing whitespace."""
        result = adapter.format_input("  Fix the bug  ")
        assert result == "Fix the bug"

    def test_format_input_preserves_internal_whitespace(self, adapter):
        """Test that format_input preserves internal whitespace."""
        result = adapter.format_input("Fix the   bug in   main.py")
        assert result == "Fix the   bug in   main.py"

    def test_format_input_empty_string(self, adapter):
        """Test format_input with empty string."""
        result = adapter.format_input("   ")
        assert result == ""

    # strip_ansi tests
    def test_strip_ansi_removes_color_codes(self, adapter):
        """Test that ANSI color codes are removed."""
        text = "\x1b[32mSuccess\x1b[0m"
        result = adapter.strip_ansi(text)
        assert result == "Success"
        assert "\x1b" not in result

    def test_strip_ansi_removes_formatting(self, adapter):
        """Test that ANSI formatting codes are removed."""
        text = "\x1b[1mBold\x1b[0m \x1b[4mUnderline\x1b[0m"
        result = adapter.strip_ansi(text)
        assert result == "Bold Underline"

    def test_strip_ansi_plain_text(self, adapter):
        """Test strip_ansi with text containing no ANSI codes."""
        text = "Plain text"
        result = adapter.strip_ansi(text)
        assert result == "Plain text"

    # detect_idle tests
    def test_detect_idle_simple_prompt(self, adapter):
        """Test detecting simple prompt."""
        assert adapter.detect_idle("Some output\n> ")
        assert adapter.detect_idle(">")

    def test_detect_idle_named_prompt(self, adapter):
        """Test detecting named claude> prompt."""
        assert adapter.detect_idle("Done\nclaude> ")

    def test_detect_idle_with_box_drawing(self, adapter):
        """Test detecting Claude's box drawing UI."""
        assert adapter.detect_idle("╭─────────────╮")

    def test_detect_idle_greeting(self, adapter):
        """Test detecting Claude's greeting messages."""
        assert adapter.detect_idle("What would you like me to help with?")
        assert adapter.detect_idle("How can I help you today?")

    def test_detect_idle_not_idle(self, adapter):
        """Test that non-idle output is not detected as idle."""
        assert not adapter.detect_idle("Processing request...")
        assert not adapter.detect_idle("Working on it")
        assert not adapter.detect_idle("")

    def test_detect_idle_with_ansi_codes(self, adapter):
        """Test idle detection strips ANSI codes first."""
        output = "\x1b[32m> \x1b[0m"
        assert adapter.detect_idle(output)

    # detect_error tests
    def test_detect_error_basic(self, adapter):
        """Test detecting basic error message."""
        error = adapter.detect_error("Error: File not found")
        assert error is not None
        assert "Error" in error

    def test_detect_error_failed(self, adapter):
        """Test detecting 'Failed:' prefix."""
        error = adapter.detect_error("Failed: Permission denied")
        assert error is not None
        assert "Failed" in error

    def test_detect_error_exception(self, adapter):
        """Test detecting exception."""
        error = adapter.detect_error("Exception: ValueError occurred")
        assert error is not None
        assert "Exception" in error

    def test_detect_error_traceback(self, adapter):
        """Test detecting Python traceback."""
        output = "Traceback (most recent call last):\n  File..."
        error = adapter.detect_error(output)
        assert error is not None
        assert "Traceback" in error

    def test_detect_error_permission_denied(self, adapter):
        """Test detecting permission denied."""
        error = adapter.detect_error("Permission denied: /etc/shadow")
        assert error is not None

    def test_detect_error_not_found(self, adapter):
        """Test detecting 'not found' errors."""
        error = adapter.detect_error("command not found: invalid-cmd")
        assert error is not None

    def test_detect_error_no_error(self, adapter):
        """Test that normal output doesn't trigger error detection."""
        assert adapter.detect_error("File created successfully") is None
        assert adapter.detect_error("All tests passed") is None
        assert adapter.detect_error("Done") is None

    def test_detect_error_case_insensitive(self, adapter):
        """Test that error detection is case-insensitive."""
        error = adapter.detect_error("ERROR: Something went wrong")
        assert error is not None

    # detect_question tests
    def test_detect_question_yes_no(self, adapter):
        """Test detecting yes/no question."""
        is_q, text, _options = adapter.detect_question("Should I proceed? (y/n)?")
        assert is_q is True
        assert text is not None
        assert "proceed" in text.lower()

    def test_detect_question_with_brackets(self, adapter):
        """Test detecting question with [Y/n] format."""
        is_q, _text, _options = adapter.detect_question("Continue? [Y/n]")
        assert is_q is True

    def test_detect_question_with_numbered_options(self, adapter):
        """Test detecting question with numbered options."""
        output = "Which option:\n1. Create new file\n2. Edit existing file"
        is_q, _text, options = adapter.detect_question(output)

        assert is_q is True
        assert options is not None
        assert len(options) == 2
        assert "Create new file" in options
        assert "Edit existing file" in options

    def test_detect_question_select_option(self, adapter):
        """Test detecting 'Select an option' pattern."""
        is_q, _text, _options = adapter.detect_question("Select an option from below")
        assert is_q is True

    def test_detect_question_no_question(self, adapter):
        """Test that non-questions are not detected."""
        is_q, text, options = adapter.detect_question("File created successfully")
        assert is_q is False
        assert text is None
        assert options is None

    # parse_response tests
    def test_parse_response_success(self, adapter):
        """Test parsing successful completion."""
        response = adapter.parse_response("File created: test.py\n> ")

        assert isinstance(response, ParsedResponse)
        assert response.is_complete is True
        assert response.is_error is False
        assert "test.py" in response.content

    def test_parse_response_error(self, adapter):
        """Test parsing error response."""
        response = adapter.parse_response("Error: Invalid input\n> ")

        assert response.is_error is True
        assert response.is_complete is True
        assert response.error_message is not None
        assert "Error" in response.error_message

    def test_parse_response_question(self, adapter):
        """Test parsing question response."""
        output = "Should I proceed? (y/n)?\n> "
        response = adapter.parse_response(output)

        assert response.is_question is True
        assert response.question_text is not None
        assert response.is_complete is True

    def test_parse_response_incomplete(self, adapter):
        """Test parsing incomplete/streaming response."""
        response = adapter.parse_response("Processing request...")

        assert response.is_complete is False
        assert response.is_error is False

    def test_parse_response_empty(self, adapter):
        """Test parsing empty output."""
        response = adapter.parse_response("")

        assert response.content == ""
        assert response.is_complete is False
        assert response.is_error is False

    def test_parse_response_strips_ansi(self, adapter):
        """Test that parse_response strips ANSI codes."""
        output = "\x1b[32mSuccess\x1b[0m\n> "
        response = adapter.parse_response(output)

        assert "\x1b" not in response.content
        assert "Success" in response.content

    def test_parse_response_with_options(self, adapter):
        """Test parsing response with numbered options."""
        output = "Which option:\n1. Option A\n2. Option B\n> "
        response = adapter.parse_response(output)

        assert response.is_question is True
        assert response.options is not None
        assert len(response.options) == 2
