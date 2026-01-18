"""Tests for base runtime adapter interfaces.

This module tests the foundational adapter interfaces, enums, and data classes
that form the contract for all runtime adapters.
"""

import pytest

from claude_mpm.commander.adapters.base import (
    Capability,
    ParsedResponse,
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeInfo,
)


class TestCapabilityEnum:
    """Test suite for Capability enum."""

    def test_capability_enum_values(self):
        """Test that Capability enum has expected values."""
        assert Capability.TOOL_USE.value == "tool_use"
        assert Capability.FILE_EDIT.value == "file_edit"
        assert Capability.FILE_CREATE.value == "file_create"
        assert Capability.GIT_OPERATIONS.value == "git_operations"
        assert Capability.SHELL_COMMANDS.value == "shell_commands"
        assert Capability.WEB_SEARCH.value == "web_search"
        assert Capability.COMPLEX_REASONING.value == "complex_reasoning"

    def test_capability_enum_members(self):
        """Test that all expected capabilities are present."""
        capabilities = set(Capability)
        assert len(capabilities) == 7
        assert Capability.TOOL_USE in capabilities
        assert Capability.FILE_EDIT in capabilities
        assert Capability.FILE_CREATE in capabilities
        assert Capability.GIT_OPERATIONS in capabilities
        assert Capability.SHELL_COMMANDS in capabilities
        assert Capability.WEB_SEARCH in capabilities
        assert Capability.COMPLEX_REASONING in capabilities


class TestRuntimeCapabilityEnum:
    """Test suite for RuntimeCapability enum."""

    def test_runtime_capability_enum_members(self):
        """Test that RuntimeCapability enum has all expected members."""
        capabilities = set(RuntimeCapability)

        # Core file operations
        assert RuntimeCapability.FILE_READ in capabilities
        assert RuntimeCapability.FILE_EDIT in capabilities
        assert RuntimeCapability.FILE_CREATE in capabilities

        # Execution capabilities
        assert RuntimeCapability.BASH_EXECUTION in capabilities
        assert RuntimeCapability.GIT_OPERATIONS in capabilities
        assert RuntimeCapability.TOOL_USE in capabilities

        # Advanced MPM features
        assert RuntimeCapability.AGENT_DELEGATION in capabilities
        assert RuntimeCapability.HOOKS in capabilities
        assert RuntimeCapability.INSTRUCTIONS in capabilities
        assert RuntimeCapability.MCP_TOOLS in capabilities
        assert RuntimeCapability.SKILLS in capabilities
        assert RuntimeCapability.MONITOR in capabilities

        # AI capabilities
        assert RuntimeCapability.WEB_SEARCH in capabilities
        assert RuntimeCapability.COMPLEX_REASONING in capabilities

        # Verify total count (14 capabilities)
        assert len(capabilities) >= 14

    def test_runtime_capability_is_auto_enum(self):
        """Test that RuntimeCapability uses auto() for values."""
        # Values should be integers from auto()
        assert isinstance(RuntimeCapability.FILE_READ.value, int)
        assert isinstance(RuntimeCapability.AGENT_DELEGATION.value, int)


class TestRuntimeInfo:
    """Test suite for RuntimeInfo dataclass."""

    def test_runtime_info_creation_basic(self):
        """Test creating RuntimeInfo with basic required fields."""
        info = RuntimeInfo(
            name="test-runtime",
            version="1.0.0",
            capabilities={RuntimeCapability.FILE_EDIT, RuntimeCapability.TOOL_USE},
            command="test-cmd",
        )

        assert info.name == "test-runtime"
        assert info.version == "1.0.0"
        assert RuntimeCapability.FILE_EDIT in info.capabilities
        assert RuntimeCapability.TOOL_USE in info.capabilities
        assert len(info.capabilities) == 2
        assert info.command == "test-cmd"
        assert info.supports_agents is False  # Default
        assert info.instruction_file is None  # Default

    def test_runtime_info_creation_full(self):
        """Test creating RuntimeInfo with all fields."""
        info = RuntimeInfo(
            name="mpm",
            version="2.0.0",
            capabilities={
                RuntimeCapability.FILE_EDIT,
                RuntimeCapability.AGENT_DELEGATION,
                RuntimeCapability.HOOKS,
            },
            command="claude",
            supports_agents=True,
            instruction_file="CLAUDE.md",
        )

        assert info.name == "mpm"
        assert info.version == "2.0.0"
        assert len(info.capabilities) == 3
        assert RuntimeCapability.AGENT_DELEGATION in info.capabilities
        assert info.command == "claude"
        assert info.supports_agents is True
        assert info.instruction_file == "CLAUDE.md"

    def test_runtime_info_without_version(self):
        """Test creating RuntimeInfo with None version."""
        info = RuntimeInfo(
            name="test",
            version=None,
            capabilities=set(),
            command="test",
        )

        assert info.version is None

    def test_runtime_info_empty_capabilities(self):
        """Test RuntimeInfo with empty capabilities set."""
        info = RuntimeInfo(
            name="basic-runtime",
            version=None,
            capabilities=set(),
            command="basic",
        )

        assert len(info.capabilities) == 0
        assert isinstance(info.capabilities, set)


class TestParsedResponse:
    """Test suite for ParsedResponse dataclass."""

    def test_parsed_response_basic(self):
        """Test creating basic ParsedResponse."""
        response = ParsedResponse(
            content="File edited successfully",
            is_complete=True,
            is_error=False,
        )

        assert response.content == "File edited successfully"
        assert response.is_complete is True
        assert response.is_error is False
        assert response.error_message is None
        assert response.is_question is False
        assert response.question_text is None
        assert response.options is None

    def test_parsed_response_with_error(self):
        """Test ParsedResponse representing an error."""
        response = ParsedResponse(
            content="Error: File not found",
            is_complete=True,
            is_error=True,
            error_message="Error: File not found: config.py",
        )

        assert response.is_error is True
        assert response.error_message == "Error: File not found: config.py"
        assert response.is_complete is True

    def test_parsed_response_with_question(self):
        """Test ParsedResponse with question and options."""
        response = ParsedResponse(
            content="Which option?\n1. Create new\n2. Edit existing",
            is_complete=True,
            is_error=False,
            is_question=True,
            question_text="Which option?",
            options=["Create new", "Edit existing"],
        )

        assert response.is_question is True
        assert response.question_text == "Which option?"
        assert response.options == ["Create new", "Edit existing"]
        assert len(response.options) == 2

    def test_parsed_response_incomplete(self):
        """Test ParsedResponse for incomplete/streaming output."""
        response = ParsedResponse(
            content="Processing...",
            is_complete=False,
            is_error=False,
        )

        assert response.is_complete is False
        assert "Processing" in response.content


class TestRuntimeAdapterInterface:
    """Test suite for RuntimeAdapter abstract interface."""

    def test_runtime_adapter_is_abstract(self):
        """Test that RuntimeAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RuntimeAdapter()

    def test_runtime_adapter_requires_abstract_methods(self):
        """Test that subclass without implementing methods cannot be instantiated."""

        class IncompleteAdapter(RuntimeAdapter):
            """Adapter missing required methods."""

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_runtime_adapter_minimal_implementation(self):
        """Test minimal valid RuntimeAdapter implementation."""

        class MinimalAdapter(RuntimeAdapter):
            """Minimal valid adapter implementation."""

            @property
            def name(self):
                return "minimal"

            @property
            def capabilities(self):
                return {Capability.TOOL_USE}

            def build_launch_command(self, project_path, agent_prompt=None):
                return f"cd {project_path} && minimal"

            def format_input(self, message):
                return message.strip()

            def detect_idle(self, output):
                return "> " in output

            def detect_error(self, output):
                if "Error:" in output:
                    return "Error detected"
                return None

            def parse_response(self, output):
                return ParsedResponse(
                    content=output,
                    is_complete=self.detect_idle(output),
                    is_error=self.detect_error(output) is not None,
                )

        # Should be instantiable now
        adapter = MinimalAdapter()
        assert adapter.name == "minimal"
        assert Capability.TOOL_USE in adapter.capabilities

        # Test methods work
        cmd = adapter.build_launch_command("/test/path")
        assert "minimal" in cmd

        formatted = adapter.format_input("  test  ")
        assert formatted == "test"

        assert adapter.detect_idle("Done\n> ")
        assert not adapter.detect_idle("Working...")

        error = adapter.detect_error("Error: failed")
        assert error == "Error detected"

    def test_runtime_info_default_implementation(self):
        """Test that runtime_info returns None by default."""

        class BasicAdapter(RuntimeAdapter):
            @property
            def name(self):
                return "basic"

            @property
            def capabilities(self):
                return set()

            def build_launch_command(self, project_path, agent_prompt=None):
                return "basic"

            def format_input(self, message):
                return message

            def detect_idle(self, output):
                return False

            def detect_error(self, output):
                return None

            def parse_response(self, output):
                return ParsedResponse(content="", is_complete=False, is_error=False)

        adapter = BasicAdapter()
        assert adapter.runtime_info is None

    def test_inject_instructions_default_implementation(self):
        """Test that inject_instructions returns None by default."""

        class NoInstructionsAdapter(RuntimeAdapter):
            @property
            def name(self):
                return "no-instructions"

            @property
            def capabilities(self):
                return set()

            def build_launch_command(self, project_path, agent_prompt=None):
                return "test"

            def format_input(self, message):
                return message

            def detect_idle(self, output):
                return False

            def detect_error(self, output):
                return None

            def parse_response(self, output):
                return ParsedResponse(content="", is_complete=False, is_error=False)

        adapter = NoInstructionsAdapter()
        result = adapter.inject_instructions("test instructions")
        assert result is None

    def test_inject_agent_context_default_implementation(self):
        """Test that inject_agent_context returns None by default."""

        class NoAgentContextAdapter(RuntimeAdapter):
            @property
            def name(self):
                return "no-context"

            @property
            def capabilities(self):
                return set()

            def build_launch_command(self, project_path, agent_prompt=None):
                return "test"

            def format_input(self, message):
                return message

            def detect_idle(self, output):
                return False

            def detect_error(self, output):
                return None

            def parse_response(self, output):
                return ParsedResponse(content="", is_complete=False, is_error=False)

        adapter = NoAgentContextAdapter()
        result = adapter.inject_agent_context("agent-001", {"role": "test"})
        assert result is None
