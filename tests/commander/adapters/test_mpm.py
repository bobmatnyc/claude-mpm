"""Tests for MPM runtime adapter.

This module comprehensively tests the MPMAdapter implementation,
including agent delegation, hooks, skills, and monitoring support.
"""

import json

import pytest

from claude_mpm.commander.adapters import Capability, RuntimeCapability
from claude_mpm.commander.adapters.mpm import MPMAdapter


class TestMPMAdapter:
    """Test suite for MPMAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a fresh adapter instance for each test."""
        return MPMAdapter()

    # Basic properties
    def test_name(self, adapter):
        """Test that adapter returns correct name."""
        assert adapter.name == "mpm"

    def test_capabilities(self, adapter):
        """Test that adapter declares full set of capabilities."""
        caps = adapter.capabilities
        assert isinstance(caps, set)

        # MPM has all capabilities
        assert Capability.TOOL_USE in caps
        assert Capability.FILE_EDIT in caps
        assert Capability.FILE_CREATE in caps
        assert Capability.GIT_OPERATIONS in caps
        assert Capability.SHELL_COMMANDS in caps
        assert Capability.WEB_SEARCH in caps
        assert Capability.COMPLEX_REASONING in caps
        assert len(caps) == 7

    def test_runtime_info_comprehensive(self, adapter):
        """Test runtime_info provides complete information."""
        info = adapter.runtime_info

        assert info is not None
        assert info.name == "mpm"
        assert info.command == "claude"  # MPM uses claude CLI
        assert info.supports_agents is True  # Key feature
        assert info.instruction_file == "CLAUDE.md"

        # Check ALL runtime capabilities - MPM has the most
        assert RuntimeCapability.FILE_READ in info.capabilities
        assert RuntimeCapability.FILE_EDIT in info.capabilities
        assert RuntimeCapability.FILE_CREATE in info.capabilities
        assert RuntimeCapability.BASH_EXECUTION in info.capabilities
        assert RuntimeCapability.GIT_OPERATIONS in info.capabilities
        assert RuntimeCapability.TOOL_USE in info.capabilities
        assert RuntimeCapability.WEB_SEARCH in info.capabilities
        assert RuntimeCapability.COMPLEX_REASONING in info.capabilities

        # MPM-specific advanced features
        assert RuntimeCapability.AGENT_DELEGATION in info.capabilities
        assert RuntimeCapability.HOOKS in info.capabilities
        assert RuntimeCapability.INSTRUCTIONS in info.capabilities
        assert RuntimeCapability.MCP_TOOLS in info.capabilities
        assert RuntimeCapability.SKILLS in info.capabilities
        assert RuntimeCapability.MONITOR in info.capabilities

    # build_launch_command tests
    def test_build_launch_command_basic(self, adapter):
        """Test basic launch command."""
        cmd = adapter.build_launch_command("/home/user/project")
        assert "cd" in cmd
        assert "claude" in cmd
        assert "--dangerously-skip-permissions" in cmd

    def test_build_launch_command_with_agent_prompt(self, adapter):
        """Test launch command with agent prompt."""
        cmd = adapter.build_launch_command("/home/user/project", "You are an engineer")
        assert "claude" in cmd
        assert "--system-prompt" in cmd
        assert "engineer" in cmd
        assert "--dangerously-skip-permissions" in cmd

    def test_build_launch_command_with_spaces(self, adapter):
        """Test launch command with path containing spaces."""
        path = "/home/user/My Projects/mpm-app"
        cmd = adapter.build_launch_command(path)
        assert "'" in cmd or '"' in cmd
        assert "claude" in cmd

    # format_input tests
    def test_format_input_strips_whitespace(self, adapter):
        """Test that format_input strips whitespace."""
        result = adapter.format_input("  test  ")
        assert result == "test"

    # strip_ansi tests
    def test_strip_ansi_removes_codes(self, adapter):
        """Test that ANSI codes are removed."""
        text = "\x1b[34mBlue\x1b[0m"
        result = adapter.strip_ansi(text)
        assert result == "Blue"
        assert "\x1b" not in result

    # detect_idle tests
    def test_detect_idle_simple_prompt(self, adapter):
        """Test detecting simple prompt."""
        assert adapter.detect_idle("Task done\n> ")

    def test_detect_idle_claude_prompt(self, adapter):
        """Test detecting claude> prompt."""
        assert adapter.detect_idle("claude> ")

    def test_detect_idle_box_drawing(self, adapter):
        """Test detecting box drawing UI."""
        assert adapter.detect_idle("╭─────╮")

    def test_detect_idle_greeting(self, adapter):
        """Test detecting greeting messages."""
        assert adapter.detect_idle("What would you like to work on?")
        assert adapter.detect_idle("How can I help?")

    def test_detect_idle_not_idle(self, adapter):
        """Test that non-idle output is not detected."""
        assert not adapter.detect_idle("Processing agent spawn...")
        assert not adapter.detect_idle("[MPM] Running hook...")

    # detect_error tests
    def test_detect_error_basic(self, adapter):
        """Test detecting basic errors."""
        error = adapter.detect_error("Error: Operation failed")
        assert error is not None
        assert "Error" in error

    def test_detect_error_agent_error(self, adapter):
        """Test detecting agent-specific errors."""
        error = adapter.detect_error("Agent error: Failed to spawn")
        assert error is not None
        assert "Agent error" in error

    def test_detect_error_hook_failed(self, adapter):
        """Test detecting hook failures."""
        error = adapter.detect_error("Hook failed: pre-commit")
        assert error is not None
        assert "Hook failed" in error

    def test_detect_error_no_error(self, adapter):
        """Test that success messages don't trigger errors."""
        assert adapter.detect_error("[MPM] Agent spawned successfully") is None
        assert adapter.detect_error("Hook triggered: pre-task") is None

    # detect_question tests
    def test_detect_question_delegate_agent(self, adapter):
        """Test detecting agent delegation question."""
        is_q, text, _options = adapter.detect_question("Delegate to which agent?")
        assert is_q is True
        assert text is not None
        assert "agent" in text.lower()

    def test_detect_question_with_options(self, adapter):
        """Test detecting questions with numbered options."""
        output = "Which option:\n1. Engineer\n2. QA\n3. PM"
        is_q, _text, options = adapter.detect_question(output)

        assert is_q is True
        assert options is not None
        assert len(options) == 3
        assert "Engineer" in options
        assert "QA" in options
        assert "PM" in options

    def test_detect_question_yes_no(self, adapter):
        """Test detecting yes/no questions."""
        is_q, _text, _options = adapter.detect_question("Run hook? (y/n)?")
        assert is_q is True

    def test_detect_question_no_question(self, adapter):
        """Test that non-questions are not detected."""
        is_q, _text, _options = adapter.detect_question("[MPM] Hook completed")
        assert is_q is False

    # parse_response tests
    def test_parse_response_success(self, adapter):
        """Test parsing successful response."""
        response = adapter.parse_response("Task completed\n> ")
        assert response.is_complete is True
        assert response.is_error is False

    def test_parse_response_error(self, adapter):
        """Test parsing error response."""
        response = adapter.parse_response("Hook failed: timeout\n> ")
        assert response.is_error is True
        assert response.error_message is not None
        assert "Hook failed" in response.error_message

    def test_parse_response_question(self, adapter):
        """Test parsing question response."""
        output = "Delegate to which agent?\n1. eng\n2. qa\n> "
        response = adapter.parse_response(output)

        assert response.is_question is True
        assert response.options is not None
        assert len(response.options) == 2

    def test_parse_response_empty(self, adapter):
        """Test parsing empty output."""
        response = adapter.parse_response("")
        assert response.content == ""
        assert response.is_complete is False

    # inject_instructions tests
    def test_inject_instructions(self, adapter):
        """Test injecting custom instructions via CLAUDE.md."""
        instructions = "You are a project manager"
        cmd = adapter.inject_instructions(instructions)

        assert cmd is not None
        assert "CLAUDE.md" in cmd
        assert "echo" in cmd
        assert "project manager" in cmd

    def test_inject_instructions_with_quotes(self, adapter):
        """Test injecting instructions with quotes (should be escaped)."""
        instructions = "You're a PM"
        cmd = adapter.inject_instructions(instructions)

        assert cmd is not None
        assert "CLAUDE.md" in cmd
        # The single quote should be properly escaped

    def test_inject_instructions_multiline(self, adapter):
        """Test injecting multiline instructions."""
        instructions = "Line 1\nLine 2\nLine 3"
        cmd = adapter.inject_instructions(instructions)

        assert cmd is not None
        assert "CLAUDE.md" in cmd

    # inject_agent_context tests
    def test_inject_agent_context_basic(self, adapter):
        """Test injecting agent context."""
        cmd = adapter.inject_agent_context("eng-001", {"role": "Engineer"})

        assert cmd is not None
        assert "MPM_AGENT_ID" in cmd
        assert "eng-001" in cmd
        assert "MPM_AGENT_CONTEXT" in cmd
        assert "export" in cmd

    def test_inject_agent_context_complex(self, adapter):
        """Test injecting complex agent context."""
        context = {
            "role": "Engineer",
            "expertise": ["Python", "JavaScript"],
            "priority": "high",
        }
        cmd = adapter.inject_agent_context("eng-002", context)

        assert cmd is not None
        assert "eng-002" in cmd
        assert "MPM_AGENT_ID" in cmd
        assert "MPM_AGENT_CONTEXT" in cmd

        # Verify context is JSON-encoded
        assert "Engineer" in cmd or "role" in cmd

    def test_inject_agent_context_with_special_chars(self, adapter):
        """Test injecting agent context with special characters."""
        context = {"note": "Test's context"}
        cmd = adapter.inject_agent_context("agent-001", context)

        assert cmd is not None
        # Should handle quotes properly

    # detect_agent_spawn tests
    def test_detect_agent_spawn_basic(self, adapter):
        """Test detecting agent spawn."""
        output = "[MPM] Agent spawned: eng-001 (Engineer)"
        info = adapter.detect_agent_spawn(output)

        assert info is not None
        assert info["agent_id"] == "eng-001"
        assert info["role"] == "Engineer"

    def test_detect_agent_spawn_different_role(self, adapter):
        """Test detecting agent spawn with different role."""
        output = "[MPM] Agent spawned: qa-002 (Quality Assurance)"
        info = adapter.detect_agent_spawn(output)

        assert info is not None
        assert info["agent_id"] == "qa-002"
        assert info["role"] == "Quality Assurance"

    def test_detect_agent_spawn_with_ansi(self, adapter):
        """Test detecting agent spawn with ANSI codes."""
        output = "\x1b[32m[MPM] Agent spawned: pm-001 (PM)\x1b[0m"
        info = adapter.detect_agent_spawn(output)

        assert info is not None
        assert info["agent_id"] == "pm-001"
        assert info["role"] == "PM"

    def test_detect_agent_spawn_no_spawn(self, adapter):
        """Test that non-spawn output returns None."""
        output = "[MPM] Hook triggered: pre-commit"
        info = adapter.detect_agent_spawn(output)

        assert info is None

    def test_detect_agent_spawn_multiple_lines(self, adapter):
        """Test detecting agent spawn in multi-line output."""
        output = "Some output\n[MPM] Agent spawned: test-001 (Tester)\nMore output"
        info = adapter.detect_agent_spawn(output)

        assert info is not None
        assert info["agent_id"] == "test-001"

    # detect_hook_trigger tests
    def test_detect_hook_trigger_basic(self, adapter):
        """Test detecting hook trigger."""
        output = "[MPM] Hook triggered: pre-commit"
        info = adapter.detect_hook_trigger(output)

        assert info is not None
        assert info["hook_name"] == "pre-commit"

    def test_detect_hook_trigger_different_hooks(self, adapter):
        """Test detecting different hook types."""
        hooks = ["pre-task", "post-task", "pre-commit", "post-commit"]

        for hook_name in hooks:
            output = f"[MPM] Hook triggered: {hook_name}"
            info = adapter.detect_hook_trigger(output)

            assert info is not None
            assert info["hook_name"] == hook_name

    def test_detect_hook_trigger_with_ansi(self, adapter):
        """Test detecting hook trigger with ANSI codes."""
        output = "\x1b[33m[MPM] Hook triggered: pre-push\x1b[0m"
        info = adapter.detect_hook_trigger(output)

        assert info is not None
        assert info["hook_name"] == "pre-push"

    def test_detect_hook_trigger_no_hook(self, adapter):
        """Test that non-hook output returns None."""
        output = "[MPM] Agent spawned: eng-001 (Engineer)"
        info = adapter.detect_hook_trigger(output)

        assert info is None

    def test_detect_hook_trigger_multiple_lines(self, adapter):
        """Test detecting hook trigger in multi-line output."""
        output = "Output\n[MPM] Hook triggered: on-error\nMore output"
        info = adapter.detect_hook_trigger(output)

        assert info is not None
        assert info["hook_name"] == "on-error"

    # Integration tests
    def test_mpm_has_most_capabilities(self, adapter):
        """Test that MPM has more capabilities than other adapters."""
        info = adapter.runtime_info

        # MPM should have at least 14 capabilities
        assert len(info.capabilities) >= 14

    def test_mpm_supports_agents_flag(self, adapter):
        """Test that MPM correctly indicates agent support."""
        info = adapter.runtime_info
        assert info.supports_agents is True

    def test_parse_response_with_mpm_patterns(self, adapter):
        """Test parsing response with MPM-specific patterns."""
        output = "[MPM] Agent spawned: eng-001 (Engineer)\n> "
        response = adapter.parse_response(output)

        # Should detect as complete (has prompt)
        assert response.is_complete is True
        assert "[MPM]" in response.content
        assert "Agent spawned" in response.content
