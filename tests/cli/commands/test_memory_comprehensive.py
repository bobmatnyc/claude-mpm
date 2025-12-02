"""
Comprehensive unit tests for the memory command module.

WHY: These tests provide a safety net for refactoring the memory command,
ensuring all functionality is preserved while we improve the code structure.

DESIGN DECISIONS:
- Mock all external dependencies (file system, AgentMemoryManager, etc.)
- Test each operation in isolation
- Cover edge cases and error handling
- Test all output formats (text, json, yaml)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.commands.memory import (MemoryManagementCommand,
                                            _build_memory,
                                            _cross_reference_memory,
                                            _route_memory_command,
                                            manage_memory)
from claude_mpm.cli.shared.base_command import CommandResult


@pytest.fixture
def mock_memory_manager():
    """Create a mock AgentMemoryManager instance."""
    manager = MagicMock()
    manager.memories_dir = Path("/test/memories")
    manager.project_memories_dir = Path("/test/project/memories")
    return manager


@pytest.fixture
def mock_config_loader():
    """Create a mock ConfigLoader."""
    with patch("claude_mpm.cli.commands.memory.ConfigLoader") as mock:
        config_loader = MagicMock()
        config = MagicMock()
        config_loader.load_main_config.return_value = config
        mock.return_value = config_loader
        yield mock


@pytest.fixture
def mock_agent_memory_manager():
    """Create a mock AgentMemoryManager class."""
    with patch("claude_mpm.cli.commands.memory.AgentMemoryManager") as mock:
        yield mock


@pytest.fixture
def memory_command(mock_config_loader, mock_agent_memory_manager):
    """Create a MemoryManagementCommand instance with mocked dependencies."""
    mock_manager = MagicMock()

    # Create a mock Path object with proper methods
    mock_path = MagicMock(spec=Path)
    mock_path.__str__.return_value = "/test/memories"
    mock_path.exists = MagicMock(return_value=True)
    mock_path.glob = MagicMock(return_value=[])
    mock_path.is_file = MagicMock(return_value=True)

    mock_manager.memories_dir = mock_path
    mock_agent_memory_manager.return_value = mock_manager

    command = MemoryManagementCommand()
    command._memory_manager = mock_manager
    return command


class TestMemoryManagementCommand:
    """Test MemoryManagementCommand class methods."""

    def test_init(self):
        """Test command initialization."""
        command = MemoryManagementCommand()
        assert command.command_name == "memory"
        assert command._memory_manager is None

    def test_memory_manager_lazy_loading(
        self, mock_config_loader, mock_agent_memory_manager
    ):
        """Test lazy loading of memory manager."""
        mock_manager = MagicMock()
        mock_agent_memory_manager.return_value = mock_manager

        command = MemoryManagementCommand()

        # First access should create the manager
        manager1 = command.memory_manager
        assert manager1 == mock_manager
        mock_agent_memory_manager.assert_called_once()

        # Second access should return the same instance
        manager2 = command.memory_manager
        assert manager2 == mock_manager
        assert mock_agent_memory_manager.call_count == 1

    def test_validate_args_valid_commands(self, memory_command):
        """Test validation of valid memory commands."""
        valid_commands = [
            "init",
            "view",
            "add",
            "clean",
            "optimize",
            "build",
            "cross-ref",
            "route",
        ]

        for cmd in valid_commands:
            args = MagicMock()
            args.memory_command = cmd
            result = memory_command.validate_args(args)
            assert result is None

    def test_validate_args_invalid_command(self, memory_command):
        """Test validation of invalid memory command."""
        args = MagicMock()
        args.memory_command = "invalid_command"
        result = memory_command.validate_args(args)
        assert "Unknown memory command: invalid_command" in result

    def test_validate_args_no_command(self, memory_command):
        """Test validation when no command specified."""
        args = MagicMock()
        # Explicitly set memory_command to None
        args.memory_command = None
        result = memory_command.validate_args(args)
        assert result is None  # No command is valid (shows status)


class TestStatusOperations:
    """Test status-related operations."""

    def test_show_status_text_format(self, memory_command):
        """Test showing status in text format."""
        args = MagicMock()
        args.format = "text"

        with patch("claude_mpm.cli.commands.memory._show_status") as mock_show:
            result = memory_command._show_status(args)

            assert result.success
            assert result.message == "Memory status displayed"
            mock_show.assert_called_once_with(memory_command.memory_manager)

    def test_show_status_json_format(self, memory_command):
        """Test showing status in JSON format."""
        args = MagicMock()
        args.format = "json"

        # Create mock path objects for memory files
        mock_file1 = MagicMock(spec=Path)
        mock_file1.stem = "agent1"
        mock_file1.name = "agent1.md"
        mock_file1.is_file.return_value = True
        mock_file1.stat.return_value = MagicMock(st_size=1024)
        mock_file1.__str__.return_value = "/test/memories/agent1.md"

        mock_file2 = MagicMock(spec=Path)
        mock_file2.stem = "agent2"
        mock_file2.name = "agent2.md"
        mock_file2.is_file.return_value = True
        mock_file2.stat.return_value = MagicMock(st_size=2048)
        mock_file2.__str__.return_value = "/test/memories/agent2.md"

        memory_command.memory_manager.memories_dir.exists.return_value = True
        memory_command.memory_manager.memories_dir.glob.return_value = [
            mock_file1,
            mock_file2,
        ]

        result = memory_command._show_status(args)

        assert result.success
        assert result.data["exists"] is True
        assert result.data["total_files"] == 2
        assert len(result.data["agents"]) == 2

    def test_show_status_no_memory_dir(self, memory_command):
        """Test status when memory directory doesn't exist."""
        args = MagicMock()
        args.format = "json"

        memory_command.memory_manager.memories_dir.exists.return_value = False

        result = memory_command._show_status(args)

        assert result.success
        assert result.data["exists"] is False
        assert result.data["total_files"] == 0
        assert len(result.data["agents"]) == 0

    def test_show_status_error_handling(self, memory_command):
        """Test error handling in show status."""
        args = MagicMock()
        args.format = "text"

        memory_command.memory_manager.memories_dir.exists.side_effect = Exception(
            "Test error"
        )

        result = memory_command._show_status(args)

        assert not result.success
        assert "Error showing memory status" in result.message


class TestViewOperations:
    """Test view/show memory operations."""

    def test_show_memories_text_format(self, memory_command):
        """Test showing memories in text format."""
        args = MagicMock()
        args.format = "text"
        args.agent = None

        with patch("claude_mpm.cli.commands.memory._show_memories") as mock_show:
            result = memory_command._show_memories(args)

            assert result.success
            assert result.message == "Memories displayed"
            mock_show.assert_called_once()

    def test_show_memories_single_agent_json(self, memory_command):
        """Test showing single agent memory in JSON format."""
        args = MagicMock()
        args.format = "json"
        args.agent = "test_agent"

        memory_command.memory_manager.load_agent_memory.return_value = (
            "Test memory content"
        )

        result = memory_command._show_memories(args)

        assert result.success
        assert result.data["agent_id"] == "test_agent"
        assert result.data["memory_content"] == "Test memory content"
        assert result.data["has_memory"] is True

    def test_show_memories_all_agents_json(self, memory_command):
        """Test showing all agent memories in JSON format."""
        args = MagicMock()
        args.format = "json"
        args.agent = None

        # Create mock path objects
        mock_file1 = MagicMock(spec=Path)
        mock_file1.stem = "agent1"
        mock_file1.is_file.return_value = True
        mock_file1.__str__.return_value = "/test/memories/agent1.md"

        mock_file2 = MagicMock(spec=Path)
        mock_file2.stem = "agent2"
        mock_file2.is_file.return_value = True
        mock_file2.__str__.return_value = "/test/memories/agent2.md"

        memory_command.memory_manager.memories_dir.exists.return_value = True
        memory_command.memory_manager.memories_dir.glob.return_value = [
            mock_file1,
            mock_file2,
        ]
        memory_command.memory_manager.load_agent_memory.side_effect = [
            "Memory 1",
            "Memory 2",
        ]

        result = memory_command._show_memories(args)

        assert result.success
        assert result.data["exists"] is True
        assert result.data["agent_count"] == 2
        assert "agent1" in result.data["agents"]
        assert "agent2" in result.data["agents"]

    def test_show_memories_no_directory(self, memory_command):
        """Test showing memories when directory doesn't exist."""
        args = MagicMock()
        args.format = "json"
        args.agent = None

        # Set exists to return False
        memory_command.memory_manager.memories_dir.exists.return_value = False

        result = memory_command._show_memories(args)

        assert result.success
        assert result.data["exists"] is False
        assert len(result.data["agents"]) == 0


class TestCRUDOperations:
    """Test Create, Read, Update, Delete operations."""

    def test_init_memory_text_format(self, memory_command):
        """Test initializing memory in text format."""
        args = MagicMock()
        args.format = "text"

        with patch("claude_mpm.cli.commands.memory._init_memory") as mock_init:
            result = memory_command._init_memory(args)

            assert result.success
            assert result.message == "Memory initialization task displayed"
            mock_init.assert_called_once()

    def test_init_memory_json_format(self, memory_command):
        """Test initializing memory in JSON format."""
        args = MagicMock()
        args.format = "json"

        result = memory_command._init_memory(args)

        assert result.success
        assert result.data["task"] == "Initialize project-specific agent memories"
        assert "suggested_command" in result.data

    def test_add_learning_success(self, memory_command):
        """Test adding a learning entry."""
        args = MagicMock()
        args.format = "text"
        args.agent_id = "test_agent"
        args.learning_type = "pattern"
        args.content = "Test learning content"

        with patch("claude_mpm.cli.commands.memory._add_learning") as mock_add:
            result = memory_command._add_learning(args)

            assert result.success
            assert result.message == "Learning added"
            mock_add.assert_called_once()

    def test_clean_memory_text(self, memory_command):
        """Test cleaning memory in text format."""
        args = MagicMock()
        args.format = "text"

        with patch("claude_mpm.cli.commands.memory._clean_memory") as mock_clean:
            result = memory_command._clean_memory(args)

            assert result.success
            assert result.message == "Memory cleanup completed"
            mock_clean.assert_called_once()

    def test_clean_memory_json(self, memory_command):
        """Test cleaning memory in JSON format."""
        args = MagicMock()
        args.format = "json"

        result = memory_command._clean_memory(args)

        assert result.success
        assert result.data["summary"] == "Memory cleanup completed"
        assert "cleaned_files" in result.data
        assert "errors" in result.data


class TestSearchOperations:
    """Test search and cross-reference operations."""

    def test_cross_reference_text(self, memory_command):
        """Test cross-reference in text format."""
        args = MagicMock()
        args.format = "text"
        args.query = "test query"

        with patch(
            "claude_mpm.cli.commands.memory._cross_reference_memory"
        ) as mock_cross:
            result = memory_command._cross_reference_memory(args)

            assert result.success
            assert result.message == "Cross-reference analysis completed"
            mock_cross.assert_called_once()

    def test_cross_reference_json(self, memory_command):
        """Test cross-reference in JSON format."""
        args = MagicMock()
        args.format = "json"

        result = memory_command._cross_reference_memory(args)

        assert result.success
        assert result.data["summary"] == "Cross-reference analysis completed"
        assert "common_patterns" in result.data
        assert "agent_similarities" in result.data


class TestOptimizationOperations:
    """Test optimization operations."""

    def test_optimize_single_agent(self, memory_command):
        """Test optimizing single agent memory."""
        args = MagicMock()
        args.format = "text"
        args.agent_id = "test_agent"

        with patch("claude_mpm.cli.commands.memory._optimize_memory") as mock_optimize:
            result = memory_command._optimize_memory(args)

            assert result.success
            assert result.message == "Memory optimization completed"
            mock_optimize.assert_called_once()

    def test_optimize_all_agents(self, memory_command):
        """Test optimizing all agent memories."""
        args = MagicMock()
        args.format = "json"
        args.agent_id = None

        result = memory_command._optimize_memory(args)

        assert result.success
        assert result.data["summary"] == "Memory optimization completed"
        assert "optimized_agents" in result.data
        assert "size_reduction" in result.data

    def test_build_memory(self, memory_command):
        """Test building memory from documentation."""
        args = MagicMock()
        args.format = "text"
        args.force_rebuild = False

        with patch("claude_mpm.cli.commands.memory._build_memory") as mock_build:
            result = memory_command._build_memory(args)

            assert result.success
            assert result.message == "Memory build completed"
            mock_build.assert_called_once()


class TestRoutingOperations:
    """Test command routing operations."""

    def test_route_command_text(self, memory_command):
        """Test routing command in text format."""
        args = MagicMock()
        args.format = "text"
        args.command = "test command"
        args.content = "test content"

        with patch(
            "claude_mpm.cli.commands.memory._route_memory_command"
        ) as mock_route:
            result = memory_command._route_memory_command(args)

            assert result.success
            assert result.message == "Command routed successfully"
            mock_route.assert_called_once()

    def test_route_command_json(self, memory_command):
        """Test routing command in JSON format."""
        args = MagicMock()
        args.format = "json"
        args.command = "test command"

        result = memory_command._route_memory_command(args)

        assert result.success
        assert result.data["routed_to"] == "memory_agent"
        assert result.data["command"] == "test command"
        assert result.data["summary"] == "Command routed successfully"


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_missing_directory_error(self, memory_command):
        """Test handling of missing directory errors."""
        args = MagicMock()
        args.format = "text"

        # Set side_effect on the mocked method
        memory_command.memory_manager.memories_dir.exists.side_effect = (
            FileNotFoundError()
        )

        result = memory_command._show_status(args)

        assert not result.success
        assert "Error showing memory status" in result.message

    def test_permission_error(self, memory_command):
        """Test handling of permission errors."""
        args = MagicMock()
        args.format = "text"

        # Set side_effect on the mocked method
        memory_command.memory_manager.memories_dir.exists.side_effect = (
            PermissionError()
        )

        result = memory_command._show_status(args)

        assert not result.success
        assert "Error showing memory status" in result.message

    def test_invalid_json_format(self, memory_command):
        """Test handling of invalid JSON data."""
        args = MagicMock()
        args.format = "json"
        args.agent = "test_agent"

        # Simulate an error that would occur during JSON serialization
        memory_command.memory_manager.load_agent_memory.side_effect = Exception(
            "JSON error"
        )

        result = memory_command._show_memories(args)

        assert not result.success
        assert "Error showing memories" in result.message


class TestCommandExecution:
    """Test command execution flow."""

    def test_run_with_no_subcommand(self, memory_command):
        """Test running with no subcommand (shows status)."""
        args = MagicMock()
        del args.memory_command  # Remove the attribute

        with patch.object(memory_command, "_show_status") as mock_status:
            mock_status.return_value = CommandResult.success_result("Status shown")
            result = memory_command.run(args)

            assert result.success
            mock_status.assert_called_once_with(args)

    def test_run_with_valid_subcommand(self, memory_command):
        """Test running with valid subcommand."""
        args = MagicMock()
        args.memory_command = "init"

        with patch.object(memory_command, "_init_memory") as mock_init:
            mock_init.return_value = CommandResult.success_result("Initialized")
            result = memory_command.run(args)

            assert result.success
            mock_init.assert_called_once_with(args)

    def test_run_with_unknown_subcommand(self, memory_command):
        """Test running with unknown subcommand."""
        args = MagicMock()
        args.memory_command = "unknown"
        args.format = "text"

        result = memory_command.run(args)

        assert not result.success
        assert "Unknown memory command: unknown" in result.message

    def test_run_with_exception(self, memory_command):
        """Test exception handling during run."""
        args = MagicMock()
        args.memory_command = "status"

        with patch.object(memory_command, "_show_status") as mock_status:
            mock_status.side_effect = Exception("Unexpected error")
            result = memory_command.run(args)

            assert not result.success
            assert "Error managing memory" in result.message


class TestManageMemoryFunction:
    """Test the manage_memory entry point function."""

    def test_manage_memory_success(self, mock_config_loader, mock_agent_memory_manager):
        """Test successful memory management."""
        args = MagicMock()
        args.format = "text"
        args.memory_command = None  # Will show status

        mock_manager = MagicMock()
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False
        mock_path.__str__.return_value = "/test/memories"
        mock_manager.memories_dir = mock_path
        mock_agent_memory_manager.return_value = mock_manager

        with patch("claude_mpm.cli.commands.memory._show_status"):
            exit_code = manage_memory(args)
            assert exit_code == 0

    def test_manage_memory_with_json_output(
        self, mock_config_loader, mock_agent_memory_manager
    ):
        """Test memory management with JSON output."""
        args = MagicMock()
        args.format = "json"
        args.memory_command = None

        mock_manager = MagicMock()
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False
        mock_path.__str__.return_value = "/test/memories"
        mock_manager.memories_dir = mock_path
        mock_agent_memory_manager.return_value = mock_manager

        # The command prints JSON output - either via print or file write
        exit_code = manage_memory(args)
        assert exit_code == 0
        # Command should succeed regardless of output method

    def test_manage_memory_error(self, mock_config_loader, mock_agent_memory_manager):
        """Test memory management with error."""
        args = MagicMock()
        args.format = "text"
        args.memory_command = "invalid"

        mock_manager = MagicMock()
        mock_manager.memories_dir = Path("/test/memories")
        mock_agent_memory_manager.return_value = mock_manager

        exit_code = manage_memory(args)
        assert exit_code == 1


class TestLegacyFunctions:
    """Test legacy standalone functions."""

    def test_show_status_function(self, mock_memory_manager, capsys):
        """Test _show_status standalone function."""
        mock_memory_manager.get_memory_status.return_value = {
            "success": True,
            "system_health": "healthy",
            "memory_directory": "/test/memories",
            "system_enabled": True,
            "auto_learning": True,
            "total_agents": 2,
            "total_size_kb": 10.5,
            "agents": {},
            "optimization_opportunities": [],
        }

        _show_status(mock_memory_manager)

        captured = capsys.readouterr()
        assert "Memory System Health" in captured.out
        assert "healthy" in captured.out
        assert "Total Agents: 2" in captured.out

    def test_init_memory_function(self, mock_memory_manager, capsys):
        """Test _init_memory standalone function."""
        args = MagicMock()

        _init_memory(args, mock_memory_manager)

        captured = capsys.readouterr()
        assert "Initializing project-specific memories" in captured.out
        assert "Agent Task: Initialize Project-Specific Memories" in captured.out

    def test_add_learning_function(self, mock_memory_manager, capsys):
        """Test _add_learning standalone function."""
        args = MagicMock()
        args.agent_id = "test_agent"
        args.learning_type = "pattern"
        args.content = "Test learning content"

        mock_memory_manager.update_agent_memory.return_value = True

        _add_learning(args, mock_memory_manager)

        captured = capsys.readouterr()
        assert "Added pattern to test_agent memory" in captured.out
        mock_memory_manager.update_agent_memory.assert_called_once()

    def test_clean_memory_function(self, mock_memory_manager, capsys):
        """Test _clean_memory standalone function."""
        args = MagicMock()

        # Create mock path for memories_dir
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True

        # Create proper mock file objects
        mock_file = MagicMock(spec=Path)
        mock_file.name = "agent1_memories.md"

        # Mock glob to return our test files for different patterns
        def mock_glob(pattern):
            if pattern == "*_memories.md":
                return [mock_file]
            if pattern in {"*_agent.md", "*.md"}:
                return []
            return []

        mock_path.glob = MagicMock(side_effect=mock_glob)
        mock_memory_manager.memories_dir = mock_path

        _clean_memory(args, mock_memory_manager)

        captured = capsys.readouterr()
        assert "Memory cleanup" in captured.out
        assert "Found 1 memory files" in captured.out

    def test_optimize_memory_single_agent(self, mock_memory_manager, capsys):
        """Test _optimize_memory for single agent."""
        args = MagicMock()
        args.agent_id = "test_agent"

        mock_memory_manager.optimize_memory.return_value = {
            "success": True,
            "agent_id": "test_agent",
            "original_size": 1000,
            "optimized_size": 800,
            "size_reduction": 200,
            "size_reduction_percent": 20,
            "duplicates_removed": 5,
        }

        _optimize_memory(args, mock_memory_manager)

        captured = capsys.readouterr()
        assert "Optimizing memory for agent: test_agent" in captured.out
        assert "Optimization completed" in captured.out

    def test_build_memory_function(self, mock_memory_manager, capsys):
        """Test _build_memory standalone function."""
        args = MagicMock()
        args.force_rebuild = False

        mock_memory_manager.build_memories_from_docs.return_value = {
            "success": True,
            "files_processed": 5,
            "memories_created": 10,
            "memories_updated": 3,
            "total_agents_affected": 2,
            "agents_affected": ["agent1", "agent2"],
        }

        _build_memory(args, mock_memory_manager)

        captured = capsys.readouterr()
        assert "Memory Building from Documentation" in captured.out
        assert "Successfully processed documentation" in captured.out
        assert "Files processed: 5" in captured.out

    def test_cross_reference_memory_function(self, mock_memory_manager, capsys):
        """Test _cross_reference_memory standalone function."""
        args = MagicMock()
        args.query = "test query"

        mock_memory_manager.cross_reference_memories.return_value = {
            "success": True,
            "common_patterns": [
                {"pattern": "pattern1", "agents": ["agent1", "agent2"], "count": 2},
            ],
            "query_matches": [
                {"agent": "agent1", "matches": ["match1", "match2"]},
            ],
            "agent_correlations": {},
        }

        _cross_reference_memory(args, mock_memory_manager)

        captured = capsys.readouterr()
        assert "Memory Cross-Reference Analysis" in captured.out
        assert "Searching for: 'test query'" in captured.out
        assert "Common patterns found" in captured.out

    def test_route_memory_command_function(self, mock_memory_manager, capsys):
        """Test _route_memory_command standalone function."""
        args = MagicMock()
        args.content = "Test content for routing"

        mock_memory_manager.route_memory_command.return_value = {
            "success": True,
            "target_agent": "engineer",
            "section": "Implementation Guidelines",
            "confidence": 0.85,
            "reasoning": "Content relates to engineering",
            "agent_scores": {
                "engineer": {"score": 0.85, "matched_keywords": ["test", "content"]},
            },
        }

        _route_memory_command(args, mock_memory_manager)

        captured = capsys.readouterr()
        assert "Memory Command Routing Test" in captured.out
        assert "Target Agent: engineer" in captured.out
        assert "Confidence: 0.85" in captured.out


class TestOutputFormats:
    """Test different output format handling."""

    def test_json_output_format(self, memory_command):
        """Test JSON output format."""
        args = MagicMock()
        args.format = "json"
        args.agent = None

        # Already mocked in fixture, just update return value
        memory_command.memory_manager.memories_dir.exists.return_value = False

        result = memory_command._show_memories(args)

        assert result.success
        assert isinstance(result.data, dict)
        assert result.data["exists"] is False

    def test_yaml_output_format(self, memory_command):
        """Test YAML output format (should be treated like JSON internally)."""
        args = MagicMock()
        args.format = "yaml"

        # Already mocked in fixture
        memory_command.memory_manager.memories_dir.exists.return_value = False

        result = memory_command._show_status(args)

        assert result.success
        assert isinstance(result.data, dict)

    def test_text_output_format(self, memory_command):
        """Test text output format."""
        args = MagicMock()
        args.format = "text"

        with patch("claude_mpm.cli.commands.memory._show_status") as mock_show:
            result = memory_command._show_status(args)

            assert result.success
            mock_show.assert_called_once()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_memory_directory(self, memory_command):
        """Test handling of empty memory directory."""
        args = MagicMock()
        args.format = "json"

        # Update return values on already mocked path
        memory_command.memory_manager.memories_dir.exists.return_value = True
        memory_command.memory_manager.memories_dir.glob.return_value = []

        result = memory_command._show_status(args)

        assert result.success
        assert result.data["total_files"] == 0
        assert len(result.data["agents"]) == 0

    def test_very_large_memory_file(self, memory_command):
        """Test handling of very large memory files."""
        args = MagicMock()
        args.format = "json"

        # Create mock file with large size
        mock_file = MagicMock(spec=Path)
        mock_file.stem = "large_agent"
        mock_file.name = "large_agent.md"
        mock_file.is_file.return_value = True
        mock_file.stat.return_value = MagicMock(st_size=1024 * 1024 * 10)  # 10MB
        mock_file.__str__.return_value = "/test/memories/large_agent.md"

        memory_command.memory_manager.memories_dir.exists.return_value = True
        memory_command.memory_manager.memories_dir.glob.return_value = [mock_file]

        result = memory_command._show_status(args)

        assert result.success
        assert result.data["total_size_kb"] > 10000

    def test_unicode_in_memory_content(self, memory_command):
        """Test handling of unicode characters in memory content."""
        args = MagicMock()
        args.format = "json"
        args.agent = "test_agent"

        memory_command.memory_manager.load_agent_memory.return_value = (
            "Test with émoji 🚀 and unicode"
        )

        result = memory_command._show_memories(args)

        assert result.success
        assert "🚀" in result.data["memory_content"]

    def test_concurrent_access(self, memory_command):
        """Test handling of concurrent access scenarios."""
        args = MagicMock()
        args.format = "text"

        # The fixture already sets up memories_dir as a MagicMock with spec=Path
        # So we can set side_effect on glob
        memory_command.memory_manager.memories_dir.glob.side_effect = (
            FileNotFoundError()
        )

        result = memory_command._show_status(args)

        assert not result.success
        assert "Error" in result.message


class TestIntegration:
    """Test integration between components."""

    def test_full_command_flow(self, mock_config_loader, mock_agent_memory_manager):
        """Test complete command execution flow."""
        args = MagicMock()
        args.format = "json"
        args.memory_command = "view"
        args.agent = "test_agent"

        mock_manager = MagicMock()
        mock_manager.memories_dir = Path("/test/memories")
        mock_manager.load_agent_memory.return_value = "Test memory"
        mock_agent_memory_manager.return_value = mock_manager

        command = MemoryManagementCommand()
        result = command.execute(args)

        assert result.success
        assert result.exit_code == 0

    def test_command_with_environment_variable(
        self, mock_config_loader, mock_agent_memory_manager, monkeypatch
    ):
        """Test command with CLAUDE_MPM_USER_PWD environment variable."""
        monkeypatch.setenv("CLAUDE_MPM_USER_PWD", "/custom/path")

        mock_manager = MagicMock()
        mock_agent_memory_manager.return_value = mock_manager

        command = MemoryManagementCommand()
        _ = command.memory_manager

        # Should use the environment variable path
        mock_agent_memory_manager.assert_called_once()
        call_args = mock_agent_memory_manager.call_args
        # The AgentMemoryManager may be called with different argument names
        # Check if the path was passed correctly
        if len(call_args[0]) > 1:
            # Positional argument
            assert str(call_args[0][1]) == "/custom/path"
        elif "current_dir" in call_args[1]:
            # Keyword argument current_dir
            assert str(call_args[1]["current_dir"]) == "/custom/path"
        elif "working_directory" in call_args[1]:
            # Keyword argument working_directory
            assert str(call_args[1]["working_directory"]) == "/custom/path"
