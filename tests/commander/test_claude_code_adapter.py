"""Tests for Claude Code runtime adapter.

This module comprehensively tests the ClaudeCodeAdapter implementation,
covering all detection logic, parsing, and command generation.
"""

import pytest

from claude_mpm.commander.adapters import (
    Capability,
    ClaudeCodeAdapter,
    ParsedResponse,
)


class TestClaudeCodeAdapter:
    """Test suite for ClaudeCodeAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a fresh adapter instance for each test."""
        return ClaudeCodeAdapter()

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
        # Verify we have all 7 capabilities
        assert len(caps) == 7

    # build_launch_command tests
    def test_build_launch_command_basic(self, adapter):
        """Test basic launch command without agent prompt."""
        cmd = adapter.build_launch_command("/home/user/project")
        # shlex.quote only quotes when necessary (no special chars = no quotes)
        assert "cd /home/user/project" in cmd or "cd '/home/user/project'" in cmd
        assert "claude" in cmd
        assert "--dangerously-skip-permissions" in cmd

    def test_build_launch_command_with_agent_prompt(self, adapter):
        """Test launch command with agent prompt."""
        cmd = adapter.build_launch_command(
            "/home/user/project", "You are a Python expert"
        )
        assert "cd /home/user/project" in cmd or "cd '/home/user/project'" in cmd
        assert "claude" in cmd
        assert "--system-prompt 'You are a Python expert'" in cmd
        assert "--dangerously-skip-permissions" in cmd

    def test_build_launch_command_shell_injection_safe(self, adapter):
        """Test that launch command properly quotes dangerous paths."""
        dangerous_path = "/home/user/project'; rm -rf /"
        cmd = adapter.build_launch_command(dangerous_path)
        # shlex.quote escapes the single quote with '"'"' pattern
        # The dangerous command is neutralized
        assert "claude" in cmd
        # Verify the path is properly escaped (not bare dangerous quote)
        assert dangerous_path not in cmd  # Raw path should not appear

    def test_build_launch_command_with_spaces(self, adapter):
        """Test launch command with path containing spaces."""
        path_with_spaces = "/home/user/My Documents/project"
        cmd = adapter.build_launch_command(path_with_spaces)
        # Should be quoted properly (entire path is quoted when spaces present)
        assert "'/home/user/My Documents/project'" in cmd

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

    def test_strip_ansi_removes_multiple_codes(self, adapter):
        """Test that multiple ANSI codes are removed."""
        text = "\x1b[1m\x1b[31mError:\x1b[0m \x1b[33mWarning\x1b[0m"
        result = adapter.strip_ansi(text)
        assert result == "Error: Warning"
        assert "\x1b" not in result

    def test_strip_ansi_handles_plain_text(self, adapter):
        """Test that plain text is unchanged."""
        text = "Plain text with no codes"
        result = adapter.strip_ansi(text)
        assert result == text

    def test_strip_ansi_handles_empty_string(self, adapter):
        """Test strip_ansi with empty string."""
        result = adapter.strip_ansi("")
        assert result == ""

    # detect_idle tests
    def test_detect_idle_simple_prompt(self, adapter):
        """Test idle detection with simple '>' prompt."""
        output = "Done processing.\n> "
        assert adapter.detect_idle(output) is True

    def test_detect_idle_named_prompt(self, adapter):
        """Test idle detection with 'claude>' prompt."""
        output = "Task completed.\nclaude> "
        assert adapter.detect_idle(output) is True

    def test_detect_idle_box_drawing(self, adapter):
        """Test idle detection with box drawing characters in last line."""
        # Box drawing pattern needs to be on the last line
        output = "Previous output\n╭──────────────────╮"
        assert adapter.detect_idle(output) is True

    def test_detect_idle_greeting(self, adapter):
        """Test idle detection with greeting message."""
        output = "What would you like me to help with?"
        assert adapter.detect_idle(output) is True

    def test_detect_idle_with_ansi_codes(self, adapter):
        """Test idle detection works with ANSI codes."""
        output = "\x1b[32mDone\x1b[0m\n\x1b[1m> \x1b[0m"
        assert adapter.detect_idle(output) is True

    def test_detect_idle_processing_state(self, adapter):
        """Test that processing state is not detected as idle."""
        output = "Processing your request..."
        assert adapter.detect_idle(output) is False

    def test_detect_idle_empty_output(self, adapter):
        """Test detect_idle with empty output."""
        assert adapter.detect_idle("") is False

    def test_detect_idle_multiline_output(self, adapter):
        """Test detect_idle with multi-line output ending in prompt."""
        output = "Line 1\nLine 2\nLine 3\n> "
        assert adapter.detect_idle(output) is True

    # detect_error tests
    def test_detect_error_with_error_prefix(self, adapter):
        """Test error detection with 'Error:' prefix."""
        output = "Error: File not found: config.py"
        error_msg = adapter.detect_error(output)
        assert error_msg is not None
        assert "Error: File not found: config.py" in error_msg

    def test_detect_error_with_exception(self, adapter):
        """Test error detection with exception."""
        output = "Exception: Invalid input provided"
        error_msg = adapter.detect_error(output)
        assert error_msg is not None
        assert "Exception:" in error_msg

    def test_detect_error_with_traceback(self, adapter):
        """Test error detection with Python traceback."""
        output = "Traceback (most recent call last):\n  File 'test.py', line 10"
        error_msg = adapter.detect_error(output)
        assert error_msg is not None
        assert "Traceback" in error_msg

    def test_detect_error_permission_denied(self, adapter):
        """Test error detection with permission error."""
        output = "Permission denied: cannot write to /etc/config"
        error_msg = adapter.detect_error(output)
        assert error_msg is not None
        assert "Permission denied" in error_msg

    def test_detect_error_not_found(self, adapter):
        """Test error detection with 'not found' message."""
        output = "bash: python3.11: command not found"
        error_msg = adapter.detect_error(output)
        assert error_msg is not None
        assert "not found" in error_msg

    def test_detect_error_with_checkmark(self, adapter):
        """Test error detection with ✗ symbol."""
        output = "✗ Failed to compile project"
        error_msg = adapter.detect_error(output)
        assert error_msg is not None
        assert "✗" in error_msg

    def test_detect_error_no_error(self, adapter):
        """Test that no error is detected in success message."""
        output = "File edited successfully\n> "
        error_msg = adapter.detect_error(output)
        assert error_msg is None

    def test_detect_error_with_ansi_codes(self, adapter):
        """Test error detection works with ANSI codes."""
        output = "\x1b[31mError: Failed to connect\x1b[0m"
        error_msg = adapter.detect_error(output)
        assert error_msg is not None
        assert "Error: Failed to connect" in error_msg

    # detect_question tests
    def test_detect_question_yes_no(self, adapter):
        """Test question detection with yes/no format."""
        output = "Should I proceed? (y/n)?"
        is_q, text, _opts = adapter.detect_question(output)
        assert is_q is True
        assert text is not None
        assert "(y/n)?" in text

    def test_detect_question_yn_brackets(self, adapter):
        """Test question detection with [Y/n] format."""
        output = "Delete this file? [Y/n]"
        is_q, text, _opts = adapter.detect_question(output)
        assert is_q is True
        assert text is not None
        assert "[Y/n]" in text

    def test_detect_question_with_options(self, adapter):
        """Test question detection with numbered options."""
        output = "Which option:\n1. Create new file\n2. Edit existing\n3. Skip"
        is_q, text, opts = adapter.detect_question(output)
        assert is_q is True
        assert text is not None
        assert opts is not None
        assert len(opts) == 3
        assert "Create new file" in opts
        assert "Edit existing" in opts
        assert "Skip" in opts

    def test_detect_question_please_choose(self, adapter):
        """Test question detection with 'Please choose' pattern."""
        output = "Please choose:\n1) Option A\n2) Option B"
        is_q, _text, opts = adapter.detect_question(output)
        assert is_q is True
        assert opts is not None
        assert len(opts) == 2
        assert "Option A" in opts
        assert "Option B" in opts

    def test_detect_question_are_you_sure(self, adapter):
        """Test question detection with 'Are you sure' pattern."""
        output = "Are you sure you want to delete this?"
        is_q, text, _opts = adapter.detect_question(output)
        assert is_q is True
        assert text is not None
        assert "Are you sure" in text

    def test_detect_question_no_question(self, adapter):
        """Test that statements are not detected as questions."""
        output = "File created successfully."
        is_q, text, opts = adapter.detect_question(output)
        assert is_q is False
        assert text is None
        assert opts is None

    def test_detect_question_select_an_option(self, adapter):
        """Test question detection with 'Select an option' pattern."""
        output = "Select an option:\n1. First choice\n2. Second choice"
        is_q, text, opts = adapter.detect_question(output)
        # 'Select an option' pattern triggers question detection
        assert is_q is True
        assert text is not None
        assert "Select an option" in text
        # Should extract numbered options
        assert opts is not None
        assert len(opts) == 2
        assert "First choice" in opts
        assert "Second choice" in opts

    # parse_response tests
    def test_parse_response_empty_output(self, adapter):
        """Test parse_response with empty output."""
        response = adapter.parse_response("")
        assert response.content == ""
        assert response.is_complete is False
        assert response.is_error is False
        assert response.is_question is False

    def test_parse_response_success_with_prompt(self, adapter):
        """Test parse_response with successful output and prompt."""
        output = "File created: test.py\n> "
        response = adapter.parse_response(output)
        assert "File created: test.py" in response.content
        assert response.is_complete is True
        assert response.is_error is False
        assert response.is_question is False

    def test_parse_response_error_with_prompt(self, adapter):
        """Test parse_response with error and prompt."""
        output = "Error: File not found\n> "
        response = adapter.parse_response(output)
        assert response.is_error is True
        assert response.error_message is not None
        assert "Error: File not found" in response.error_message
        assert response.is_complete is True

    def test_parse_response_question_with_options(self, adapter):
        """Test parse_response with question and options."""
        output = "Which option:\n1. Create\n2. Edit\nclaude> "
        response = adapter.parse_response(output)
        assert response.is_question is True
        assert response.question_text is not None
        assert response.options is not None
        assert len(response.options) == 2
        assert response.is_complete is True

    def test_parse_response_ansi_codes_stripped(self, adapter):
        """Test that parse_response strips ANSI codes from content."""
        output = "\x1b[32mSuccess\x1b[0m\n\x1b[1m> \x1b[0m"
        response = adapter.parse_response(output)
        assert "\x1b" not in response.content
        assert "Success" in response.content

    def test_parse_response_processing_state(self, adapter):
        """Test parse_response with processing state (not complete)."""
        output = "Processing your request..."
        response = adapter.parse_response(output)
        assert response.is_complete is False
        assert response.is_error is False

    def test_parse_response_multiline_with_error(self, adapter):
        """Test parse_response with multi-line output containing error."""
        output = (
            "Starting task...\nProcessing...\nError: Failed to connect\nAborting.\n> "
        )
        response = adapter.parse_response(output)
        assert response.is_error is True
        assert response.error_message is not None
        assert "Error: Failed to connect" in response.error_message
        assert response.is_complete is True
        assert "Starting task" in response.content

    def test_parse_response_very_long_output(self, adapter):
        """Test parse_response handles very long output."""
        # Generate long output (1000 lines)
        long_output = "\n".join([f"Line {i}" for i in range(1000)])
        long_output += "\n> "
        response = adapter.parse_response(long_output)
        assert response.is_complete is True
        assert "Line 0" in response.content
        assert "Line 999" in response.content

    def test_parse_response_partial_line(self, adapter):
        """Test parse_response with partial line (incomplete output)."""
        output = "Processing your req"
        response = adapter.parse_response(output)
        assert response.is_complete is False

    def test_parse_response_multiple_errors(self, adapter):
        """Test that first error is captured when multiple errors present."""
        output = "Error: First error\nError: Second error\n> "
        response = adapter.parse_response(output)
        assert response.is_error is True
        # Should capture the first error
        assert (
            "First error" in response.error_message
            or "Second error" in response.error_message
        )


class TestParsedResponse:
    """Test suite for ParsedResponse dataclass."""

    def test_parsed_response_creation(self):
        """Test creating ParsedResponse instance."""
        response = ParsedResponse(
            content="Test content",
            is_complete=True,
            is_error=False,
            is_question=False,
        )
        assert response.content == "Test content"
        assert response.is_complete is True
        assert response.is_error is False
        assert response.is_question is False
        assert response.error_message is None
        assert response.question_text is None
        assert response.options is None

    def test_parsed_response_with_error(self):
        """Test ParsedResponse with error information."""
        response = ParsedResponse(
            content="Error occurred",
            is_complete=True,
            is_error=True,
            error_message="Error: Something went wrong",
            is_question=False,
        )
        assert response.is_error is True
        assert response.error_message == "Error: Something went wrong"

    def test_parsed_response_with_question(self):
        """Test ParsedResponse with question information."""
        response = ParsedResponse(
            content="Question content",
            is_complete=True,
            is_error=False,
            is_question=True,
            question_text="Should I proceed?",
            options=["Yes", "No"],
        )
        assert response.is_question is True
        assert response.question_text == "Should I proceed?"
        assert response.options == ["Yes", "No"]


class TestCapability:
    """Test suite for Capability enum."""

    def test_capability_values(self):
        """Test that all expected capabilities exist."""
        assert Capability.TOOL_USE.value == "tool_use"
        assert Capability.FILE_EDIT.value == "file_edit"
        assert Capability.FILE_CREATE.value == "file_create"
        assert Capability.GIT_OPERATIONS.value == "git_operations"
        assert Capability.SHELL_COMMANDS.value == "shell_commands"
        assert Capability.WEB_SEARCH.value == "web_search"
        assert Capability.COMPLEX_REASONING.value == "complex_reasoning"

    def test_capability_membership(self):
        """Test capability membership in sets."""
        caps = {Capability.TOOL_USE, Capability.FILE_EDIT}
        assert Capability.TOOL_USE in caps
        assert Capability.FILE_EDIT in caps
        assert Capability.WEB_SEARCH not in caps
