#!/usr/bin/env python3
"""
Unit tests for Memory CLI Subcommands.

Tests all memory CLI subcommands (status, view, add, clean, build, show, route).
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


class TestMemoryStatusCommand:
    """Test memory status command functionality."""

    def test_show_status_with_data(self):
        """Test showing status with memory data."""
        self.get_memory_status.return_value = {
            "total_agents": 5,
            "total_memories": 8,
            "memory_size_kb": 250,
            "agents_with_memory": ["engineer", "qa", "research"],
            "largest_memory_agent": "engineer",
            "largest_memory_size_kb": 100,
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_status(self)

        output = mock_stdout.getvalue()
        assert "Memory Status" in output
        assert "5 agents" in output
        assert "8 memories" in output
        assert "250 KB" in output
        assert "engineer" in output

    def test_show_status_no_data(self):
        """Test showing status with no memory data."""
        self.get_memory_status.return_value = {
            "total_agents": 0,
            "total_memories": 0,
            "memory_size_kb": 0,
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_status(self)

        output = mock_stdout.getvalue()
        assert "Memory Status" in output
        assert "0 agents" in output
        assert "0 memories" in output

    def test_show_status_error_handling(self):
        """Test status command error handling."""
        self.get_memory_status.side_effect = Exception("Status error")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_status(self)

        output = mock_stdout.getvalue()
        assert "Error" in output or "status error" in output.lower()


class TestMemoryViewCommand:
    """Test memory view command functionality."""

    def test_view_memory_success(self):
        """Test viewing memory content successfully."""
        self.load_agent_memory.return_value = (
            "# Engineer Memory\n## Patterns\n- Use dependency injection"
        )

        args = Namespace(agent_id="engineer")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _view_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Memory for agent: engineer" in output
        assert "Use dependency injection" in output

    def test_view_memory_not_found(self):
        """Test viewing memory when agent has no memory."""
        self.load_agent_memory.return_value = None

        args = Namespace(agent_id="nonexistent")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _view_memory(args, self)

        output = mock_stdout.getvalue()
        assert "No memory found for agent: nonexistent" in output

    def test_view_memory_file_not_found(self):
        """Test viewing memory when file doesn't exist."""
        self.load_agent_memory.side_effect = FileNotFoundError("File not found")

        args = Namespace(agent_id="missing")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _view_memory(args, self)

        output = mock_stdout.getvalue()
        assert "No memory file found for agent: missing" in output

    def test_view_memory_error_handling(self):
        """Test view memory error handling."""
        self.load_agent_memory.side_effect = Exception("Read error")

        args = Namespace(agent_id="error_agent")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _view_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Error viewing memory" in output


class TestMemoryAddCommand:
    """Test memory add command functionality."""

    def test_add_learning_success(self):
        """Test adding learning successfully."""
        self.add_learning.return_value = True

        args = Namespace(
            agent_id="engineer",
            learning_type="pattern",
            content="Use factory pattern for object creation",
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _add_learning(args, self)

        output = mock_stdout.getvalue()
        assert "Learning added successfully" in output

        # Verify the method was called with correct arguments
        self.add_learning.assert_called_once_with(
            "engineer", "pattern", "Use factory pattern for object creation"
        )

    def test_add_learning_failure(self):
        """Test adding learning when it fails."""
        self.add_learning.return_value = False

        args = Namespace(
            agent_id="engineer", learning_type="pattern", content="Test pattern"
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _add_learning(args, self)

        output = mock_stdout.getvalue()
        assert "Failed to add learning" in output

    def test_add_learning_error_handling(self):
        """Test add learning error handling."""
        self.add_learning.side_effect = Exception("Add error")

        args = Namespace(
            agent_id="engineer", learning_type="pattern", content="Test pattern"
        )

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _add_learning(args, self)

        output = mock_stdout.getvalue()
        assert "Error adding learning" in output


class TestMemoryCleanCommand:
    """Test memory clean command functionality."""

    def test_clean_memory_with_files(self):
        """Test cleaning memory when files exist."""
        # Mock memory directory with files
        self.memories_dir = Path("/test/memories")

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob",
            return_value=[
                Path("/test/memories/engineer_agent.md"),
                Path("/test/memories/qa_agent.md"),
            ],
        ), patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            args = Namespace()
            _clean_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Memory cleanup" in output
        assert "2 memory files found" in output

    def test_clean_memory_no_directory(self):
        """Test cleaning memory when directory doesn't exist."""
        self.memories_dir = Path("/test/nonexistent")

        with patch("pathlib.Path.exists", return_value=False), patch(
            "sys.stdout", new_callable=StringIO
        ) as mock_stdout:
            args = Namespace()
            _clean_memory(args, self)

        output = mock_stdout.getvalue()
        assert "No memory directory found" in output

    def test_clean_memory_no_files(self):
        """Test cleaning memory when no files exist."""
        self.memories_dir = Path("/test/memories")

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob", return_value=[]
        ), patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            args = Namespace()
            _clean_memory(args, self)

        output = mock_stdout.getvalue()
        assert "No memory files found" in output


class TestMemoryBuildCommand:
    """Test memory build command functionality."""

    def test_build_memory_success(self):
        """Test building memory from documentation successfully."""
        self.build_memories_from_docs.return_value = {
            "success": True,
            "agents_updated": ["engineer", "qa"],
            "patterns_extracted": 15,
            "total_learnings": 25,
        }

        args = Namespace(force_rebuild=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _build_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Memory Building from Documentation" in output
        assert "2 agents updated" in output
        assert "15 patterns extracted" in output
        assert "25 total learnings" in output

    def test_build_memory_with_force_rebuild(self):
        """Test building memory with force rebuild flag."""
        self.build_memories_from_docs.return_value = {
            "success": True,
            "agents_updated": ["engineer"],
            "patterns_extracted": 5,
            "total_learnings": 10,
        }

        args = Namespace(force_rebuild=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _build_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Memory Building from Documentation" in output

        # Verify force_rebuild was passed
        self.build_memories_from_docs.assert_called_once_with(True)

    def test_build_memory_failure(self):
        """Test building memory when it fails."""
        self.build_memories_from_docs.return_value = {
            "success": False,
            "error": "No documentation found",
        }

        args = Namespace(force_rebuild=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _build_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Failed to build memories" in output
        assert "No documentation found" in output

    def test_build_memory_error_handling(self):
        """Test build memory error handling."""
        self.build_memories_from_docs.side_effect = Exception("Build error")

        args = Namespace(force_rebuild=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _build_memory(args, self)

        output = mock_stdout.getvalue()
        assert "Error building memories" in output


class TestMemoryShowCommand:
    """Test memory show command functionality."""

    def test_show_memories_single_agent(self):
        """Test showing memories for a single agent."""
        self.load_agent_memory.return_value = """# Engineer Memory
## Patterns
- Use dependency injection
- Follow SOLID principles
## Context
- Project uses microservices
## Recent Learnings
- New testing framework adopted"""

        args = Namespace(agent_id="engineer", format="detailed", raw=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, self)

        output = mock_stdout.getvalue()
        assert "Agent: engineer" in output
        assert "Patterns" in output
        assert "dependency injection" in output

    def test_show_memories_all_agents_summary(self):
        """Test showing memories for all agents in summary format."""
        self.memories_dir = Path("/test/memories")

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob",
            return_value=[
                Path("/test/memories/engineer_agent.md"),
                Path("/test/memories/qa_agent.md"),
            ],
        ), patch.object(
            self,
            "load_agent_memory",
            side_effect=[
                "# Engineer\n## Patterns\n- Pattern 1\n- Pattern 2",
                "# QA\n## Context\n- Context 1",
            ],
        ), patch(
            "sys.stdout", new_callable=StringIO
        ) as mock_stdout:
            args = Namespace(agent_id=None, format="summary", raw=False)
            _show_memories(args, self)

        output = mock_stdout.getvalue()
        assert "Found memories for 2 agents" in output
        assert "engineer" in output
        assert "qa" in output

    def test_show_memories_raw_output_single(self):
        """Test showing single agent memory in raw JSON format."""
        self.get_agent_memory_raw.return_value = {
            "agent_id": "engineer",
            "sections": {
                "patterns": ["Pattern 1", "Pattern 2"],
                "context": ["Context 1"],
            },
            "metadata": {"last_updated": "2024-01-01T00:00:00Z", "total_items": 3},
        }

        args = Namespace(agent_id="engineer", raw=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, self)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert data["agent_id"] == "engineer"
        assert "patterns" in data["sections"]
        assert len(data["sections"]["patterns"]) == 2

    def test_show_memories_raw_output_all(self):
        """Test showing all agent memories in raw JSON format."""
        self.get_all_memories_raw.return_value = {
            "agents": {
                "engineer": {
                    "sections": {"patterns": ["Pattern 1"]},
                    "metadata": {"total_items": 1},
                },
                "qa": {
                    "sections": {"context": ["Context 1"]},
                    "metadata": {"total_items": 1},
                },
            },
            "summary": {"total_agents": 2, "total_items": 2},
        }

        args = Namespace(agent_id=None, raw=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, self)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert "agents" in data
        assert "engineer" in data["agents"]
        assert "qa" in data["agents"]
        assert data["summary"]["total_agents"] == 2

    def test_show_memories_error_handling_raw(self):
        """Test show memories error handling in raw mode."""
        self.get_agent_memory_raw.side_effect = Exception("Raw error")

        args = Namespace(agent_id="engineer", raw=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, self)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        assert data["success"] is False
        assert "Raw error" in data["error"]


class TestMemoryRouteCommand:
    """Test memory route command functionality."""

    def test_route_memory_command_success(self):
        """Test routing memory command successfully."""
        self.route_memory_command.return_value = {
            "success": True,
            "target_agent": "engineer",
            "section": "patterns",
            "confidence": 0.85,
            "reasoning": "Content mentions design patterns and code structure",
        }

        args = Namespace(content="Use factory pattern for object creation")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _route_memory_subcommand(args, self)

        output = mock_stdout.getvalue()
        assert "Memory Command Routing Test" in output
        assert "Target Agent: engineer" in output
        assert "Section: patterns" in output
        assert "Confidence: 0.85" in output
        assert "design patterns" in output

    def test_route_memory_command_no_content(self):
        """Test routing memory command without content."""
        args = Namespace(content=None)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _route_memory_subcommand(args, self)

        output = mock_stdout.getvalue()
        assert "No content provided for routing analysis" in output
        assert "Usage: memory route --content" in output

    def test_route_memory_command_failure(self):
        """Test routing memory command when routing fails."""
        self.route_memory_command.return_value = {
            "success": False,
            "error": "Unable to determine target agent",
        }

        args = Namespace(content="Ambiguous content")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _route_memory_subcommand(args, self)

        output = mock_stdout.getvalue()
        assert "Routing failed" in output
        assert "Unable to determine target agent" in output

    def test_route_memory_command_error_handling(self):
        """Test route memory command error handling."""
        self.route_memory_command.side_effect = Exception("Route error")

        args = Namespace(content="Test content")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _route_memory_subcommand(args, self)

        output = mock_stdout.getvalue()
        assert "Error routing memory command" in output


class TestMemoryUtilityFunctions:
    """Test utility functions used by memory commands."""

    def test_parse_memory_content():
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

    def test_parse_memory_content_empty():
        """Test parsing empty memory content."""
        content = ""
        sections = _parse_memory_content(content)
        assert sections == {}

    def test_parse_memory_content_no_sections():
        """Test parsing memory content without sections."""
        content = "Just some text without sections"
        sections = _parse_memory_content(content)
        assert sections == {}
