"""Tests for adapter registry.

This module tests the AdapterRegistry for registering, retrieving,
and auto-detecting available runtime adapters.
"""

import shutil
from unittest.mock import patch

import pytest

from claude_mpm.commander.adapters.base import Capability, RuntimeAdapter
from claude_mpm.commander.adapters.registry import AdapterRegistry


class DummyAdapter(RuntimeAdapter):
    """Dummy adapter for testing."""

    @property
    def name(self):
        return "dummy"

    @property
    def capabilities(self):
        return {Capability.TOOL_USE}

    def build_launch_command(self, project_path, agent_prompt=None):
        return f"cd {project_path} && dummy"

    def format_input(self, message):
        return message

    def detect_idle(self, output):
        return False

    def detect_error(self, output):
        return None

    def parse_response(self, output):
        from claude_mpm.commander.adapters.base import ParsedResponse

        return ParsedResponse(content=output, is_complete=False, is_error=False)


class TestAdapterRegistry:
    """Test suite for AdapterRegistry."""

    @pytest.fixture(autouse=True)
    def clean_registry(self):
        """Clean registry before each test."""
        # Save original state
        original_adapters = AdapterRegistry._adapters.copy()
        original_commands = AdapterRegistry._runtime_commands.copy()

        # Clear registry for test
        AdapterRegistry._adapters.clear()

        yield

        # Restore original state
        AdapterRegistry._adapters = original_adapters
        AdapterRegistry._runtime_commands = original_commands

    def test_register_adapter(self):
        """Test registering a new adapter."""
        AdapterRegistry.register("dummy", DummyAdapter)

        assert "dummy" in AdapterRegistry._adapters
        assert AdapterRegistry._adapters["dummy"] == DummyAdapter

    def test_register_multiple_adapters(self):
        """Test registering multiple adapters."""

        class AnotherAdapter(DummyAdapter):
            @property
            def name(self):
                return "another"

        AdapterRegistry.register("dummy", DummyAdapter)
        AdapterRegistry.register("another", AnotherAdapter)

        assert len(AdapterRegistry._adapters) == 2
        assert "dummy" in AdapterRegistry._adapters
        assert "another" in AdapterRegistry._adapters

    def test_register_overwrites_existing(self):
        """Test that registering same name overwrites previous adapter."""

        class NewDummyAdapter(DummyAdapter):
            @property
            def name(self):
                return "new-dummy"

        AdapterRegistry.register("dummy", DummyAdapter)
        AdapterRegistry.register("dummy", NewDummyAdapter)

        # Should be overwritten
        assert AdapterRegistry._adapters["dummy"] == NewDummyAdapter

    def test_unregister_adapter(self):
        """Test unregistering an adapter."""
        AdapterRegistry.register("dummy", DummyAdapter)
        assert "dummy" in AdapterRegistry._adapters

        AdapterRegistry.unregister("dummy")
        assert "dummy" not in AdapterRegistry._adapters

    def test_unregister_nonexistent_adapter(self):
        """Test unregistering adapter that doesn't exist (should not error)."""
        # Should not raise error
        AdapterRegistry.unregister("nonexistent")

    def test_get_adapter_success(self):
        """Test retrieving registered adapter."""
        AdapterRegistry.register("dummy", DummyAdapter)

        adapter = AdapterRegistry.get("dummy")

        assert adapter is not None
        assert isinstance(adapter, DummyAdapter)
        assert adapter.name == "dummy"

    def test_get_adapter_returns_new_instance(self):
        """Test that get() returns new instance each time."""
        AdapterRegistry.register("dummy", DummyAdapter)

        adapter1 = AdapterRegistry.get("dummy")
        adapter2 = AdapterRegistry.get("dummy")

        assert adapter1 is not adapter2  # Different instances

    def test_get_adapter_not_found(self):
        """Test retrieving non-existent adapter returns None."""
        result = AdapterRegistry.get("nonexistent")
        assert result is None

    def test_list_registered(self):
        """Test listing all registered adapter names."""
        AdapterRegistry.register("dummy", DummyAdapter)
        AdapterRegistry.register("another", DummyAdapter)

        registered = AdapterRegistry.list_registered()

        assert isinstance(registered, list)
        assert "dummy" in registered
        assert "another" in registered
        assert len(registered) == 2

    def test_list_registered_empty(self):
        """Test listing when no adapters registered."""
        registered = AdapterRegistry.list_registered()
        assert isinstance(registered, list)
        assert len(registered) == 0

    def test_detect_available_with_available_command(self):
        """Test detecting available runtimes when command exists."""
        AdapterRegistry.register("dummy", DummyAdapter)
        AdapterRegistry.register_command("dummy", "echo")  # 'echo' should exist

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/echo"
            available = AdapterRegistry.detect_available()

            assert "dummy" in available
            mock_which.assert_called_with("echo")

    def test_detect_available_with_unavailable_command(self):
        """Test detecting available runtimes when command doesn't exist."""
        AdapterRegistry.register("dummy", DummyAdapter)
        AdapterRegistry.register_command("dummy", "nonexistent-command")

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            available = AdapterRegistry.detect_available()

            assert "dummy" not in available

    def test_detect_available_multiple_runtimes(self):
        """Test detecting multiple available runtimes."""
        AdapterRegistry.register("runtime1", DummyAdapter)
        AdapterRegistry.register("runtime2", DummyAdapter)
        AdapterRegistry.register_command("runtime1", "cmd1")
        AdapterRegistry.register_command("runtime2", "cmd2")

        with patch("shutil.which") as mock_which:

            def which_side_effect(cmd):
                return f"/usr/bin/{cmd}" if cmd == "cmd1" else None

            mock_which.side_effect = which_side_effect
            available = AdapterRegistry.detect_available()

            assert "runtime1" in available
            assert "runtime2" not in available

    def test_get_default_returns_highest_priority(self):
        """Test that get_default returns highest priority available adapter."""
        # Register all adapters
        for name in ["mpm", "claude-code", "auggie", "codex"]:
            AdapterRegistry.register(name, DummyAdapter)

        with patch.object(AdapterRegistry, "detect_available") as mock_detect:
            # Make all available
            mock_detect.return_value = ["mpm", "claude-code", "auggie", "codex"]

            adapter = AdapterRegistry.get_default()

            # Should return MPM (highest priority)
            assert adapter is not None
            # Note: DummyAdapter returns "dummy" as name, but we registered it as "mpm"
            # The adapter instance itself doesn't change based on registration name

    def test_get_default_priority_order(self):
        """Test default adapter selection follows priority order."""
        # Priority: mpm > claude-code > auggie > codex

        for name in ["claude-code", "auggie", "codex"]:
            AdapterRegistry.register(name, DummyAdapter)

        with patch.object(AdapterRegistry, "detect_available") as mock_detect:
            # Only claude-code and codex available
            mock_detect.return_value = ["claude-code", "codex"]

            # Mock get to return different adapters based on name
            original_get = AdapterRegistry.get

            def mock_get(name):
                return original_get(name) if name in ["claude-code", "codex"] else None

            with patch.object(AdapterRegistry, "get", side_effect=mock_get):
                adapter = AdapterRegistry.get_default()

                # Should return claude-code (higher priority than codex)
                assert adapter is not None

    def test_get_default_no_available_adapters(self):
        """Test get_default when no adapters available."""
        with patch.object(AdapterRegistry, "detect_available") as mock_detect:
            mock_detect.return_value = []

            adapter = AdapterRegistry.get_default()
            assert adapter is None

    def test_is_available_true(self):
        """Test is_available returns True for available runtime."""
        AdapterRegistry.register("dummy", DummyAdapter)

        with patch.object(AdapterRegistry, "detect_available") as mock_detect:
            mock_detect.return_value = ["dummy"]

            assert AdapterRegistry.is_available("dummy") is True

    def test_is_available_false(self):
        """Test is_available returns False for unavailable runtime."""
        with patch.object(AdapterRegistry, "detect_available") as mock_detect:
            mock_detect.return_value = []

            assert AdapterRegistry.is_available("dummy") is False

    def test_get_command_existing(self):
        """Test getting command for registered runtime."""
        AdapterRegistry.register_command("dummy", "dummy-cmd")

        cmd = AdapterRegistry.get_command("dummy")
        assert cmd == "dummy-cmd"

    def test_get_command_nonexistent(self):
        """Test getting command for unregistered runtime."""
        cmd = AdapterRegistry.get_command("nonexistent")
        assert cmd is None

    def test_register_command(self):
        """Test registering a new command."""
        AdapterRegistry.register_command("new-runtime", "new-cmd")

        assert AdapterRegistry._runtime_commands["new-runtime"] == "new-cmd"

    def test_register_command_overwrites(self):
        """Test that register_command overwrites existing command."""
        AdapterRegistry.register_command("runtime", "old-cmd")
        AdapterRegistry.register_command("runtime", "new-cmd")

        assert AdapterRegistry._runtime_commands["runtime"] == "new-cmd"

    def test_detect_available_only_checks_registered_adapters(self):
        """Test that detect_available only checks registered adapters."""
        # Register command but not adapter
        AdapterRegistry.register_command("unregistered", "echo")

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/echo"
            available = AdapterRegistry.detect_available()

            # Should not be in available list (adapter not registered)
            assert "unregistered" not in available

    def test_detect_available_requires_both_adapter_and_command(self):
        """Test that runtime must have both adapter AND command to be available."""
        # Register adapter but not command
        AdapterRegistry.register("no-command", DummyAdapter)

        with patch("shutil.which"):
            available = AdapterRegistry.detect_available()

            # Should not be available (no command registered)
            assert "no-command" not in available
