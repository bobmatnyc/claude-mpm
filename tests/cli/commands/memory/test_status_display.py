#!/usr/bin/env python3
"""
Unit tests for Memory Status and Display.

Tests memory status reporting and display functions.
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


class TestMemoryStatusAndDisplay:
    """Test memory status and display functions."""

    @pytest.fixture
    def mock_memory_manager(self):
        """Create mock memory manager with comprehensive status."""
        manager = Mock(spec=AgentMemoryManager)
        manager.memories_dir = Path("/test/.claude/memories")
        manager.get_memory_status.return_value = {
            "success": True,
            "system_enabled": True,
            "auto_learning": True,
            "memory_directory": "/test/.claude/memories",
            "system_health": "healthy",
            "total_agents": 2,
            "total_size_kb": 100,
            "agents": {
                "engineer": {
                    "size_kb": 60,
                    "size_limit_kb": 80,
                    "size_utilization": 75,
                    "sections": 4,
                    "items": 15,
                    "last_modified": "2025-01-01T12:00:00Z",
                    "auto_learning": True,
                },
                "qa": {
                    "size_kb": 40,
                    "size_limit_kb": 80,
                    "size_utilization": 50,
                    "sections": 3,
                    "items": 10,
                    "last_modified": "2025-01-01T11:00:00Z",
                    "auto_learning": True,
                },
            },
        }
        return manager

    def test_show_status_displays_system_health(self):
        """Test _show_status displays system health information."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_status(self)

        output = mock_stdout.getvalue()
        assert "Memory System Health" in output
        assert "healthy" in output
        assert "System Enabled: Yes" in output
        assert "Auto Learning: Yes" in output

    def test_show_status_displays_agent_information(self):
        """Test _show_status displays individual agent information."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_status(self)

        output = mock_stdout.getvalue()
        assert "engineer" in output
        assert "qa" in output
        assert "75%" in output  # engineer utilization
        assert "50%" in output  # qa utilization
        assert "15 items" in output  # engineer items
        assert "10 items" in output  # qa items

    def test_show_status_handles_no_memory_directory():
        """Test _show_status handles missing memory directory."""
        manager = Mock(spec=AgentMemoryManager)
        manager.get_memory_status.return_value = {
            "success": True,
            "system_health": "no_memory_dir",
            "memory_directory": "/nonexistent",
            "system_enabled": True,
            "auto_learning": True,
            "total_agents": 0,
            "agents": {},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_status(manager)

        output = mock_stdout.getvalue()
        assert "no_memory_dir" in output or "No memory" in output

    def test_show_basic_status_fallback():
        """Test _show_basic_status fallback functionality."""
        from claude_mpm.cli.commands.memory import _show_basic_status

        manager = Mock(spec=AgentMemoryManager)
        manager.memories_dir = Path("/test/memories")
        manager.memories_dir.exists.return_value = False

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_basic_status(manager)

        output = mock_stdout.getvalue()
        assert "Basic Status" in output
        assert "not found" in output

    def test_show_memories_all_agents(self):
        """Test _show_memories displays all agent memories."""
        self.load_agent_memory.side_effect = (
            lambda agent: f"# {agent} Memory\n- Test content"
        )

        args = Namespace(agent=None, format="summary", raw=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, self)

        output = mock_stdout.getvalue()
        assert "Agent Memories Display" in output

    def test_show_memories_single_agent(self):
        """Test _show_memories displays single agent memory."""
        self.load_agent_memory.return_value = (
            "# Engineer Memory\n## Patterns\n- Test pattern"
        )

        args = Namespace(agent="engineer", format="detailed", raw=False)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, self)

        output = mock_stdout.getvalue()
        assert "Agent Memories Display" in output

    def test_show_memories_raw_output(self):
        """Test _show_memories with raw JSON output."""
        self.load_agent_memory.return_value = "# Test Memory"

        args = Namespace(agent="engineer", format="summary", raw=True)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            _show_memories(args, self)

        output = mock_stdout.getvalue()
        # Should output JSON format
        try:
            json.loads(output)
            json_valid = True
        except:
            json_valid = False
        assert json_valid

    def test_parse_memory_content_extracts_sections():
        """Test _parse_memory_content extracts memory sections correctly."""
        memory_content = """# Agent Memory

## Coding Patterns Learned
- Use dependency injection
- Follow SOLID principles

## Implementation Guidelines
- Write unit tests first
- Use meaningful variable names

## Common Mistakes to Avoid
- Don't ignore error handling
"""

        sections = _parse_memory_content(memory_content)

        assert "Coding Patterns Learned" in sections
        assert "Implementation Guidelines" in sections
        assert "Common Mistakes to Avoid" in sections

        assert len(sections["Coding Patterns Learned"]) == 2
        assert len(sections["Implementation Guidelines"]) == 2
        assert len(sections["Common Mistakes to Avoid"]) == 1

        assert "Use dependency injection" in sections["Coding Patterns Learned"]
        assert "Write unit tests first" in sections["Implementation Guidelines"]

    def test_parse_memory_content_handles_empty_sections():
        """Test _parse_memory_content handles empty sections."""
        memory_content = """# Agent Memory

## Empty Section

## Section With Content
- Some content
"""

        sections = _parse_memory_content(memory_content)

        assert "Empty Section" in sections
        assert "Section With Content" in sections
        assert len(sections["Empty Section"]) == 0
        assert len(sections["Section With Content"]) == 1


