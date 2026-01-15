"""Tests for CommandParser."""

import pytest

from claude_mpm.commander.chat.commands import (
    Command,
    CommandParser,
    CommandType,
)


@pytest.fixture
def parser():
    """Create a CommandParser instance."""
    return CommandParser()


def test_parse_list_command(parser):
    """Test parsing 'list' command."""
    cmd = parser.parse("list")

    assert cmd is not None
    assert cmd.type == CommandType.LIST
    assert cmd.args == []
    assert cmd.raw == "list"


def test_parse_start_command_with_args(parser):
    """Test parsing 'start' command with arguments."""
    cmd = parser.parse("start /path/to/project --framework cc")

    assert cmd is not None
    assert cmd.type == CommandType.START
    assert cmd.args == ["/path/to/project", "--framework", "cc"]


def test_parse_connect_command(parser):
    """Test parsing 'connect' command."""
    cmd = parser.parse("connect myapp")

    assert cmd is not None
    assert cmd.type == CommandType.CONNECT
    assert cmd.args == ["myapp"]


def test_parse_alias_ls(parser):
    """Test parsing 'ls' alias for 'list'."""
    cmd = parser.parse("ls")

    assert cmd is not None
    assert cmd.type == CommandType.LIST


def test_parse_alias_instances(parser):
    """Test parsing 'instances' alias for 'list'."""
    cmd = parser.parse("instances")

    assert cmd is not None
    assert cmd.type == CommandType.LIST


def test_parse_alias_quit(parser):
    """Test parsing 'quit' alias for 'exit'."""
    cmd = parser.parse("quit")

    assert cmd is not None
    assert cmd.type == CommandType.EXIT


def test_parse_alias_q(parser):
    """Test parsing 'q' alias for 'exit'."""
    cmd = parser.parse("q")

    assert cmd is not None
    assert cmd.type == CommandType.EXIT


def test_parse_natural_language(parser):
    """Test that natural language returns None."""
    cmd = parser.parse("tell me about the code")

    assert cmd is None


def test_parse_empty_string(parser):
    """Test that empty string returns None."""
    cmd = parser.parse("")

    assert cmd is None


def test_is_command_true(parser):
    """Test is_command returns True for built-in commands."""
    assert parser.is_command("list")
    assert parser.is_command("start /path")
    assert parser.is_command("ls")
    assert parser.is_command("quit")


def test_is_command_false(parser):
    """Test is_command returns False for natural language."""
    assert not parser.is_command("tell me about the code")
    assert not parser.is_command("")


def test_parse_all_command_types(parser):
    """Test parsing all command types."""
    commands = [
        ("list", CommandType.LIST),
        ("start", CommandType.START),
        ("stop", CommandType.STOP),
        ("connect", CommandType.CONNECT),
        ("disconnect", CommandType.DISCONNECT),
        ("status", CommandType.STATUS),
        ("help", CommandType.HELP),
        ("exit", CommandType.EXIT),
    ]

    for cmd_str, expected_type in commands:
        cmd = parser.parse(cmd_str)
        assert cmd is not None
        assert cmd.type == expected_type


def test_parse_case_insensitive(parser):
    """Test that parsing is case-insensitive."""
    cmd = parser.parse("LIST")

    assert cmd is not None
    assert cmd.type == CommandType.LIST
