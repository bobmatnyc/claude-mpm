#!/usr/bin/env python3
"""
Unit tests for Memory Utilities and Routing.

Tests memory command routing and utility functions.
"""

import json
from argparse import Namespace
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.cli.commands.memory import (
    MemoryManagementCommand,
    _build_memory,
    _cross_reference_memory,
    manage_memory,
)
from claude_mpm.cli.shared.base_command import CommandResult
from claude_mpm.services.agents.memory import AgentMemoryManager


class TestMemoryUtilitiesAndRouting:
    """Test memory command utilities and routing functions."""

    @pytest.fixture
    def mock_memory_manager(self):
        """Create mock memory manager."""
        manager = Mock(spec=AgentMemoryManager)
        manager.add_learning.return_value = True
        manager.update_agent_memory.return_value = True
        return manager

    def test_add_learning_with_valid_parameters(self):
        """Test _add_learning with valid parameters."""
        args = Namespace(
            agent="engineer",
            learning_type="pattern",
            content="Use factory pattern for object creation",
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _add_learning(args, self)

        output = mock_stdout.getvalue()
        assert "Added learning" in output or "Learning added" in output
        self.add_learning.assert_called_once_with(
            "engineer", "pattern", "Use factory pattern for object creation"
        )

    def test_add_learning_handles_failure(self):
        """Test _add_learning handles failure gracefully."""
        self.add_learning.return_value = False

        args = Namespace(
            agent="engineer", learning_type="pattern", content="Test content"
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _add_learning(args, self)

        output = mock_stdout.getvalue()
        assert "Failed" in output or "Error" in output

    def test_init_memory_displays_instructions(self):
        """Test _init_memory displays initialization instructions."""
        args = Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _init_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Memory Initialization Task" in output
        assert "claude-mpm memory add" in output
        assert "Example commands" in output

    def test_clean_memory_shows_cleanup_info(self):
        """Test _clean_memory shows cleanup information."""
        self.memories_dir = Path("/test/memories")
        self.memories_dir.exists.return_value = True

        args = Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _clean_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Memory cleanup" in output

    def test_clean_memory_handles_no_directory(self):
        """Test _clean_memory handles missing memory directory."""
        self.memories_dir = Path("/nonexistent")
        self.memories_dir.exists.return_value = False

        args = Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _clean_memory(args, self)

        output = mock_stdout.getvalue()
        assert "No memory directory" in output or "nothing to clean" in output

    def test_build_memory_displays_build_info(self):
        """Test _build_memory displays build information."""
        args = Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _build_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Memory building" in output or "Build memory" in output

    def test_optimize_memory_displays_optimization_info(self):
        """Test _optimize_memory displays optimization information."""
        args = Namespace(agent=None)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _optimize_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Memory optimization" in output or "Optimize memory" in output

    def test_route_memory_command_displays_routing_info(self):
        """Test _route_memory_command displays routing information."""
        args = Namespace(command="test command")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _route_memory_subcommand(args, self)

        output = mock_stdout.getvalue()
        assert "Memory command routing" in output or "Route command" in output

    def test_cross_reference_memory_displays_cross_ref_info(self):
        """Test _cross_reference_memory displays cross-reference information."""
        args = Namespace()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _cross_reference_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Cross-reference" in output or "Memory cross" in output

    def test_manage_memory_function_calls_command():
        """Test manage_memory function calls MemoryManagementCommand."""
        args = Namespace(memory_command="status", format="text")

        with patch(
            "claude_mpm.cli.commands.memory.MemoryManagementCommand"
        ) as mock_command_class:
            mock_command = Mock()
            mock_result = Mock()
            mock_result.exit_code = 0
            mock_command.execute.return_value = mock_result
            mock_command_class.return_value = mock_command

            exit_code = manage_memory(args)

            assert exit_code == 0
            mock_command.execute.assert_called_once_with(args)

    def test_manage_memory_backward_compatibility():
        """Test manage_memory maintains backward compatibility."""
        args = Namespace(memory_command="status", format="text")

        with patch(
            "claude_mpm.cli.commands.memory.MemoryManagementCommand"
        ) as mock_command_class:
            mock_command = Mock()
            mock_result = Mock()
            mock_result.exit_code = 0
            mock_command.execute.return_value = mock_result
            mock_command_class.return_value = mock_command

            exit_code = manage_memory(args)

            # Should return exit code
            assert exit_code == 0
            mock_command.execute.assert_called_once_with(args)

    def test_output_single_agent_raw_json_format(self):
        """Test _output_single_agent_raw outputs valid JSON."""
        self.load_agent_memory.return_value = "# Test Memory\n- Test item"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _output_single_agent_raw("engineer", self)

        output = mock_stdout.getvalue()

        # Should be valid JSON
        try:
            data = json.loads(output)
            assert "agent_id" in data
            assert "memory_content" in data
            assert data["agent_id"] == "engineer"
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    def test_output_all_memories_raw_json_format(self):
        """Test _output_all_memories_raw outputs valid JSON."""
        self.memories_dir = Path("/test/memories")
        self.memories_dir.exists.return_value = True

        # Mock glob to return test files
        mock_file1 = Mock()
        mock_file1.is_file.return_value = True
        mock_file1.stem = "engineer_memories"

        mock_file2 = Mock()
        mock_file2.is_file.return_value = True
        mock_file2.stem = "qa_memories"

        self.memories_dir.glob.return_value = [mock_file1, mock_file2]
        self.load_agent_memory.side_effect = lambda agent: f"# {agent} Memory"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _output_all_memories_raw(self)

        output = mock_stdout.getvalue()

        # Should be valid JSON
        try:
            data = json.loads(output)
            assert "agents" in data
            assert "timestamp" in data
            assert isinstance(data["agents"], dict)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    @patch("claude_mpm.cli.commands.memory.AgentMemoryManager")
    @patch("claude_mpm.cli.commands.memory.Config")
    def test_execute_memory_command_status(self, mock_manager_class):
        """Test executing memory status command."""
        # Setup mocks
        mock_config = Mock()
        self.return_value = mock_config

        mock_manager = Mock()
        mock_manager.get_memory_status.return_value = {
            "total_agents": 2,
            "total_memories": 3,
            "memory_size_kb": 100,
        }
        mock_manager_class.return_value = mock_manager

        args = Namespace(memory_command="status")

        # Capture output
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = execute_memory_subcommand(args)

        # Verify
        assert result is None  # Success returns None
        output = mock_stdout.getvalue()
        assert "Memory Status" in output
        assert "2 agents" in output
        assert "3 memories" in output

    @patch("claude_mpm.cli.commands.memory.AgentMemoryManager")
    @patch("claude_mpm.cli.commands.memory.Config")
    def test_execute_memory_command_no_subcommand(
        self, mock_config_class, mock_manager_class
    ):
        """Test executing memory command without subcommand shows status."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_manager = Mock()
        mock_manager.get_memory_status.return_value = {
            "total_agents": 1,
            "total_memories": 1,
            "memory_size_kb": 50,
        }
        mock_manager_class.return_value = mock_manager

        args = Namespace(memory_command=None)

        # Capture output
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = execute_memory_subcommand(args)

        # Verify
        assert result is None
        output = mock_stdout.getvalue()
        assert "Memory Status" in output

    @patch("claude_mpm.cli.commands.memory.AgentMemoryManager")
    @patch("claude_mpm.cli.commands.memory.Config")
    def test_execute_memory_command_unknown(
        self, mock_config_class, mock_manager_class
    ):
        """Test executing unknown memory command."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        args = Namespace(memory_command="unknown_command")

        # Capture output
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = execute_memory_subcommand(args)

        # Verify
        assert result == 1  # Error return code
        output = mock_stdout.getvalue()
        assert "Unknown memory command" in output
        assert "unknown_command" in output


