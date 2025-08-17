#!/usr/bin/env python3
"""
Comprehensive unit tests for Memory CLI commands.

This test suite provides complete coverage for the memory CLI functionality
including:
- Memory command routing and argument parsing
- Memory status, view, add, clean operations
- Memory building and optimization
- Cross-reference and routing functionality
- Error handling and edge cases
- Raw output formatting
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace
from io import StringIO
import sys

# Import the functions we're testing
from claude_mpm.cli.commands.memory import (
    execute_memory_command,
    _show_status,
    _show_memories,
    _add_learning,
    _clean_memory,
    _optimize_memory,
    _build_memory,
    _cross_reference_memory,
    _route_memory_command,
    _init_memory,
    _view_memory,
    _parse_memory_content,
    _output_single_agent_raw,
    _output_all_memories_raw
)
from claude_mpm.services.agents.memory import AgentMemoryManager
from claude_mpm.core.config import Config


class TestMemoryCommandExecution:
    """Test main memory command execution and routing."""
    
    @pytest.fixture
    def mock_memory_manager(self):
        """Create a mock AgentMemoryManager."""
        manager = Mock(spec=AgentMemoryManager)
        manager.memories_dir = Path("/test/memories")
        manager.load_agent_memory.return_value = "# Test Memory\n## Patterns\n- Test pattern"
        manager.get_memory_status.return_value = {
            "total_agents": 3,
            "total_memories": 5,
            "memory_size_kb": 150
        }
        return manager
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock Config."""
        config = Mock(spec=Config)
        return config
    
    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    @patch('claude_mpm.cli.commands.memory.Config')
    def test_execute_memory_command_status(self, mock_config_class, mock_manager_class):
        """Test executing memory status command."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_manager = Mock()
        mock_manager.get_memory_status.return_value = {
            "total_agents": 2,
            "total_memories": 3,
            "memory_size_kb": 100
        }
        mock_manager_class.return_value = mock_manager
        
        args = Namespace(memory_command="status")
        
        # Capture output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = execute_memory_command(args)
        
        # Verify
        assert result is None  # Success returns None
        output = mock_stdout.getvalue()
        assert "Memory Status" in output
        assert "2 agents" in output
        assert "3 memories" in output
    
    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    @patch('claude_mpm.cli.commands.memory.Config')
    def test_execute_memory_command_no_subcommand(self, mock_config_class, mock_manager_class):
        """Test executing memory command without subcommand shows status."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_manager = Mock()
        mock_manager.get_memory_status.return_value = {
            "total_agents": 1,
            "total_memories": 1,
            "memory_size_kb": 50
        }
        mock_manager_class.return_value = mock_manager
        
        args = Namespace(memory_command=None)
        
        # Capture output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = execute_memory_command(args)
        
        # Verify
        assert result is None
        output = mock_stdout.getvalue()
        assert "Memory Status" in output
    
    @patch('claude_mpm.cli.commands.memory.AgentMemoryManager')
    @patch('claude_mpm.cli.commands.memory.Config')
    def test_execute_memory_command_unknown(self, mock_config_class, mock_manager_class):
        """Test executing unknown memory command."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        args = Namespace(memory_command="unknown_command")
        
        # Capture output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = execute_memory_command(args)
        
        # Verify
        assert result == 1  # Error return code
        output = mock_stdout.getvalue()
        assert "Unknown memory command" in output
        assert "unknown_command" in output


class TestMemoryStatusCommand:
    """Test memory status command functionality."""
    
    def test_show_status_with_data(self, mock_memory_manager):
        """Test showing status with memory data."""
        mock_memory_manager.get_memory_status.return_value = {
            "total_agents": 5,
            "total_memories": 8,
            "memory_size_kb": 250,
            "agents_with_memory": ["engineer", "qa", "research"],
            "largest_memory_agent": "engineer",
            "largest_memory_size_kb": 100
        }
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_status(mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "Memory Status" in output
        assert "5 agents" in output
        assert "8 memories" in output
        assert "250 KB" in output
        assert "engineer" in output
    
    def test_show_status_no_data(self, mock_memory_manager):
        """Test showing status with no memory data."""
        mock_memory_manager.get_memory_status.return_value = {
            "total_agents": 0,
            "total_memories": 0,
            "memory_size_kb": 0
        }
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_status(mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "Memory Status" in output
        assert "0 agents" in output
        assert "0 memories" in output
    
    def test_show_status_error_handling(self, mock_memory_manager):
        """Test status command error handling."""
        mock_memory_manager.get_memory_status.side_effect = Exception("Status error")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_status(mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "Error" in output or "status error" in output.lower()


class TestMemoryViewCommand:
    """Test memory view command functionality."""
    
    def test_view_memory_success(self, mock_memory_manager):
        """Test viewing memory content successfully."""
        mock_memory_manager.load_agent_memory.return_value = "# Engineer Memory\n## Patterns\n- Use dependency injection"
        
        args = Namespace(agent_id="engineer")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _view_memory(args, mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "Memory for agent: engineer" in output
        assert "Use dependency injection" in output
    
    def test_view_memory_not_found(self, mock_memory_manager):
        """Test viewing memory when agent has no memory."""
        mock_memory_manager.load_agent_memory.return_value = None
        
        args = Namespace(agent_id="nonexistent")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _view_memory(args, mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "No memory found for agent: nonexistent" in output
    
    def test_view_memory_file_not_found(self, mock_memory_manager):
        """Test viewing memory when file doesn't exist."""
        mock_memory_manager.load_agent_memory.side_effect = FileNotFoundError("File not found")
        
        args = Namespace(agent_id="missing")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _view_memory(args, mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "No memory file found for agent: missing" in output
    
    def test_view_memory_error_handling(self, mock_memory_manager):
        """Test view memory error handling."""
        mock_memory_manager.load_agent_memory.side_effect = Exception("Read error")
        
        args = Namespace(agent_id="error_agent")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _view_memory(args, mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "Error viewing memory" in output


class TestMemoryAddCommand:
    """Test memory add command functionality."""
    
    def test_add_learning_success(self, mock_memory_manager):
        """Test adding learning successfully."""
        mock_memory_manager.add_learning.return_value = True
        
        args = Namespace(
            agent_id="engineer",
            learning_type="pattern",
            content="Use factory pattern for object creation"
        )
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _add_learning(args, mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "Learning added successfully" in output
        
        # Verify the method was called with correct arguments
        mock_memory_manager.add_learning.assert_called_once_with(
            "engineer", "pattern", "Use factory pattern for object creation"
        )
    
    def test_add_learning_failure(self, mock_memory_manager):
        """Test adding learning when it fails."""
        mock_memory_manager.add_learning.return_value = False
        
        args = Namespace(
            agent_id="engineer",
            learning_type="pattern",
            content="Test pattern"
        )
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _add_learning(args, mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "Failed to add learning" in output
    
    def test_add_learning_error_handling(self, mock_memory_manager):
        """Test add learning error handling."""
        mock_memory_manager.add_learning.side_effect = Exception("Add error")
        
        args = Namespace(
            agent_id="engineer",
            learning_type="pattern",
            content="Test pattern"
        )
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _add_learning(args, mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "Error adding learning" in output


class TestMemoryCleanCommand:
    """Test memory clean command functionality."""
    
    def test_clean_memory_with_files(self, mock_memory_manager):
        """Test cleaning memory when files exist."""
        # Mock memory directory with files
        mock_memory_manager.memories_dir = Path("/test/memories")
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.glob', return_value=[
                 Path("/test/memories/engineer_agent.md"),
                 Path("/test/memories/qa_agent.md")
             ]), \
             patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            
            args = Namespace()
            _clean_memory(args, mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "Memory cleanup" in output
        assert "2 memory files found" in output
    
    def test_clean_memory_no_directory(self, mock_memory_manager):
        """Test cleaning memory when directory doesn't exist."""
        mock_memory_manager.memories_dir = Path("/test/nonexistent")
        
        with patch('pathlib.Path.exists', return_value=False), \
             patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            
            args = Namespace()
            _clean_memory(args, mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "No memory directory found" in output
    
    def test_clean_memory_no_files(self, mock_memory_manager):
        """Test cleaning memory when no files exist."""
        mock_memory_manager.memories_dir = Path("/test/memories")
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.glob', return_value=[]), \
             patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            
            args = Namespace()
            _clean_memory(args, mock_memory_manager)
        
        output = mock_stdout.getvalue()
        assert "No memory files found" in output


class TestMemoryBuildCommand:
    """Test memory build command functionality."""

    def test_build_memory_success(self, mock_memory_manager):
        """Test building memory from documentation successfully."""
        mock_memory_manager.build_memories_from_docs.return_value = {
            "success": True,
            "agents_updated": ["engineer", "qa"],
            "patterns_extracted": 15,
            "total_learnings": 25
        }

        args = Namespace(force_rebuild=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _build_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory Building from Documentation" in output
        assert "2 agents updated" in output
        assert "15 patterns extracted" in output
        assert "25 total learnings" in output

    def test_build_memory_with_force_rebuild(self, mock_memory_manager):
        """Test building memory with force rebuild flag."""
        mock_memory_manager.build_memories_from_docs.return_value = {
            "success": True,
            "agents_updated": ["engineer"],
            "patterns_extracted": 5,
            "total_learnings": 10
        }

        args = Namespace(force_rebuild=True)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _build_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory Building from Documentation" in output

        # Verify force_rebuild was passed
        mock_memory_manager.build_memories_from_docs.assert_called_once_with(True)

    def test_build_memory_failure(self, mock_memory_manager):
        """Test building memory when it fails."""
        mock_memory_manager.build_memories_from_docs.return_value = {
            "success": False,
            "error": "No documentation found"
        }

        args = Namespace(force_rebuild=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _build_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Failed to build memories" in output
        assert "No documentation found" in output

    def test_build_memory_error_handling(self, mock_memory_manager):
        """Test build memory error handling."""
        mock_memory_manager.build_memories_from_docs.side_effect = Exception("Build error")

        args = Namespace(force_rebuild=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _build_memory(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Error building memories" in output


class TestMemoryShowCommand:
    """Test memory show command functionality."""

    def test_show_memories_single_agent(self, mock_memory_manager):
        """Test showing memories for a single agent."""
        mock_memory_manager.load_agent_memory.return_value = """# Engineer Memory
## Patterns
- Use dependency injection
- Follow SOLID principles
## Context
- Project uses microservices
## Recent Learnings
- New testing framework adopted"""

        args = Namespace(agent_id="engineer", format="detailed", raw=False)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Agent: engineer" in output
        assert "Patterns" in output
        assert "dependency injection" in output

    def test_show_memories_all_agents_summary(self, mock_memory_manager):
        """Test showing memories for all agents in summary format."""
        mock_memory_manager.memories_dir = Path("/test/memories")

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.glob', return_value=[
                 Path("/test/memories/engineer_agent.md"),
                 Path("/test/memories/qa_agent.md")
             ]), \
             patch.object(mock_memory_manager, 'load_agent_memory', side_effect=[
                 "# Engineer\n## Patterns\n- Pattern 1\n- Pattern 2",
                 "# QA\n## Context\n- Context 1"
             ]), \
             patch('sys.stdout', new_callable=StringIO) as mock_stdout:

            args = Namespace(agent_id=None, format="summary", raw=False)
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Found memories for 2 agents" in output
        assert "engineer" in output
        assert "qa" in output

    def test_show_memories_raw_output_single(self, mock_memory_manager):
        """Test showing single agent memory in raw JSON format."""
        mock_memory_manager.get_agent_memory_raw.return_value = {
            "agent_id": "engineer",
            "sections": {
                "patterns": ["Pattern 1", "Pattern 2"],
                "context": ["Context 1"]
            },
            "metadata": {
                "last_updated": "2024-01-01T00:00:00Z",
                "total_items": 3
            }
        }

        args = Namespace(agent_id="engineer", raw=True)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert data["agent_id"] == "engineer"
        assert "patterns" in data["sections"]
        assert len(data["sections"]["patterns"]) == 2

    def test_show_memories_raw_output_all(self, mock_memory_manager):
        """Test showing all agent memories in raw JSON format."""
        mock_memory_manager.get_all_memories_raw.return_value = {
            "agents": {
                "engineer": {
                    "sections": {"patterns": ["Pattern 1"]},
                    "metadata": {"total_items": 1}
                },
                "qa": {
                    "sections": {"context": ["Context 1"]},
                    "metadata": {"total_items": 1}
                }
            },
            "summary": {
                "total_agents": 2,
                "total_items": 2
            }
        }

        args = Namespace(agent_id=None, raw=True)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert "agents" in data
        assert "engineer" in data["agents"]
        assert "qa" in data["agents"]
        assert data["summary"]["total_agents"] == 2

    def test_show_memories_error_handling_raw(self, mock_memory_manager):
        """Test show memories error handling in raw mode."""
        mock_memory_manager.get_agent_memory_raw.side_effect = Exception("Raw error")

        args = Namespace(agent_id="engineer", raw=True)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _show_memories(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert data["success"] is False
        assert "Raw error" in data["error"]


class TestMemoryRouteCommand:
    """Test memory route command functionality."""

    def test_route_memory_command_success(self, mock_memory_manager):
        """Test routing memory command successfully."""
        mock_memory_manager.route_memory_command.return_value = {
            "success": True,
            "target_agent": "engineer",
            "section": "patterns",
            "confidence": 0.85,
            "reasoning": "Content mentions design patterns and code structure"
        }

        args = Namespace(content="Use factory pattern for object creation")

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _route_memory_command(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Memory Command Routing Test" in output
        assert "Target Agent: engineer" in output
        assert "Section: patterns" in output
        assert "Confidence: 0.85" in output
        assert "design patterns" in output

    def test_route_memory_command_no_content(self, mock_memory_manager):
        """Test routing memory command without content."""
        args = Namespace(content=None)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _route_memory_command(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "No content provided for routing analysis" in output
        assert "Usage: memory route --content" in output

    def test_route_memory_command_failure(self, mock_memory_manager):
        """Test routing memory command when routing fails."""
        mock_memory_manager.route_memory_command.return_value = {
            "success": False,
            "error": "Unable to determine target agent"
        }

        args = Namespace(content="Ambiguous content")

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _route_memory_command(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Routing failed" in output
        assert "Unable to determine target agent" in output

    def test_route_memory_command_error_handling(self, mock_memory_manager):
        """Test route memory command error handling."""
        mock_memory_manager.route_memory_command.side_effect = Exception("Route error")

        args = Namespace(content="Test content")

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            _route_memory_command(args, mock_memory_manager)

        output = mock_stdout.getvalue()
        assert "Error routing memory command" in output


class TestMemoryUtilityFunctions:
    """Test utility functions used by memory commands."""

    def test_parse_memory_content(self):
        """Test parsing memory content into sections."""
        content = """# Agent Memory
## Patterns
- Pattern 1
- Pattern 2

## Context
- Context item 1
- Context item 2

## Recent Learnings
- Learning 1"""

        sections = _parse_memory_content(content)

        assert "Patterns" in sections
        assert "Context" in sections
        assert "Recent Learnings" in sections
        assert len(sections["Patterns"]) == 2
        assert len(sections["Context"]) == 2
        assert len(sections["Recent Learnings"]) == 1
        assert "Pattern 1" in sections["Patterns"]

    def test_parse_memory_content_empty(self):
        """Test parsing empty memory content."""
        content = ""
        sections = _parse_memory_content(content)
        assert sections == {}

    def test_parse_memory_content_no_sections(self):
        """Test parsing memory content without sections."""
        content = "Just some text without sections"
        sections = _parse_memory_content(content)
        assert sections == {}
