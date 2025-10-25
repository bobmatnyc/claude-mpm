"""
Unit tests for configure.py methods.

WHY: These tests verify individual methods in isolation using mocks to ensure
each method behaves correctly before refactoring.

DESIGN: Each test focuses on a single method, using mocks for dependencies,
and tests both happy paths and error cases.

TARGET: 85%+ coverage of all 68 methods in configure.py

Part of: TSK-0056 Configure.py Refactoring - Phase 1: Test Coverage
"""

import json
import sys
import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest
from rich.console import Console
from rich.table import Table

from claude_mpm.cli.commands.configure import (
    AgentConfig,
    ConfigureCommand,
    SimpleAgentManager,
)
from claude_mpm.cli.shared import CommandResult


# ==============================================================================
# SimpleAgentManager Unit Tests
# ==============================================================================


class TestSimpleAgentManager:
    """Unit tests for SimpleAgentManager class."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary configuration directory."""
        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @pytest.fixture
    def agent_manager(self, temp_config_dir):
        """Create SimpleAgentManager instance."""
        return SimpleAgentManager(temp_config_dir)

    # Test 1: __init__
    def test_init_creates_directory(self, tmp_path):
        """Test that __init__ creates config directory if missing."""
        config_dir = tmp_path / "new_dir" / ".claude-mpm"
        assert not config_dir.exists()

        manager = SimpleAgentManager(config_dir)

        assert config_dir.exists()
        assert manager.config_dir == config_dir
        assert manager.config_file == config_dir / "agent_states.json"

    # Test 2: _load_states - file exists
    def test_load_states_file_exists(self, temp_config_dir):
        """Test loading states from existing file."""
        states_file = temp_config_dir / "agent_states.json"
        test_states = {"engineer": {"enabled": True}, "designer": {"enabled": False}}
        states_file.write_text(json.dumps(test_states))

        manager = SimpleAgentManager(temp_config_dir)

        assert manager.states == test_states

    # Test 3: _load_states - file missing
    def test_load_states_file_missing(self, temp_config_dir):
        """Test loading states when file doesn't exist."""
        manager = SimpleAgentManager(temp_config_dir)

        assert manager.states == {}

    # Test 4: _save_states
    def test_save_states(self, agent_manager):
        """Test saving states to file."""
        agent_manager.states = {"qa": {"enabled": True}}
        agent_manager._save_states()

        saved_data = json.loads(agent_manager.config_file.read_text())
        assert saved_data == {"qa": {"enabled": True}}

    # Test 5: is_agent_enabled - True
    def test_is_agent_enabled_true(self, agent_manager):
        """Test checking enabled agent."""
        agent_manager.states = {"engineer": {"enabled": True}}

        assert agent_manager.is_agent_enabled("engineer") is True

    # Test 6: is_agent_enabled - False
    def test_is_agent_enabled_false(self, agent_manager):
        """Test checking disabled agent."""
        agent_manager.states = {"designer": {"enabled": False}}

        assert agent_manager.is_agent_enabled("designer") is False

    # Test 7: is_agent_enabled - default (not in states)
    def test_is_agent_enabled_default(self, agent_manager):
        """Test checking agent not in states (should default to True)."""
        assert agent_manager.is_agent_enabled("unknown") is True

    # Test 8: set_agent_enabled - enable
    def test_set_agent_enabled_true(self, agent_manager):
        """Test enabling an agent."""
        agent_manager.set_agent_enabled("engineer", True)

        assert agent_manager.states["engineer"]["enabled"] is True
        # Verify it was saved
        saved_data = json.loads(agent_manager.config_file.read_text())
        assert saved_data["engineer"]["enabled"] is True

    # Test 9: set_agent_enabled - disable
    def test_set_agent_enabled_false(self, agent_manager):
        """Test disabling an agent."""
        agent_manager.set_agent_enabled("designer", False)

        assert agent_manager.states["designer"]["enabled"] is False

    # Test 10: set_agent_enabled - updates existing
    def test_set_agent_enabled_updates_existing(self, agent_manager):
        """Test updating existing agent state."""
        agent_manager.set_agent_enabled("qa", True)
        agent_manager.set_agent_enabled("qa", False)

        assert agent_manager.states["qa"]["enabled"] is False

    # Test 11: set_agent_enabled_deferred
    def test_set_agent_enabled_deferred(self, agent_manager):
        """Test deferred state change."""
        agent_manager.set_agent_enabled_deferred("engineer", False)

        assert agent_manager.deferred_changes["engineer"] is False
        # Should NOT be in states yet
        assert "engineer" not in agent_manager.states

    # Test 12: commit_deferred_changes
    def test_commit_deferred_changes(self, agent_manager):
        """Test committing deferred changes."""
        agent_manager.set_agent_enabled_deferred("engineer", True)
        agent_manager.set_agent_enabled_deferred("designer", False)

        agent_manager.commit_deferred_changes()

        assert agent_manager.states["engineer"]["enabled"] is True
        assert agent_manager.states["designer"]["enabled"] is False
        # Verify saved to file
        saved_data = json.loads(agent_manager.config_file.read_text())
        assert saved_data["engineer"]["enabled"] is True

    # Test 13: discard_deferred_changes
    def test_discard_deferred_changes(self, agent_manager):
        """Test discarding deferred changes."""
        agent_manager.set_agent_enabled_deferred("engineer", False)
        assert agent_manager.has_pending_changes() is True

        agent_manager.discard_deferred_changes()

        assert agent_manager.has_pending_changes() is False
        assert len(agent_manager.deferred_changes) == 0

    # Test 14: get_pending_state - has pending
    def test_get_pending_state_has_pending(self, agent_manager):
        """Test getting pending state."""
        agent_manager.set_agent_enabled_deferred("engineer", False)

        assert agent_manager.get_pending_state("engineer") is False

    # Test 15: get_pending_state - no pending
    def test_get_pending_state_no_pending(self, agent_manager):
        """Test getting pending state when none exists."""
        agent_manager.states = {"engineer": {"enabled": True}}

        # Should return current state from states dict
        assert agent_manager.get_pending_state("engineer") is True

    # Test 16: has_pending_changes - True
    def test_has_pending_changes_true(self, agent_manager):
        """Test has_pending_changes when changes exist."""
        agent_manager.set_agent_enabled_deferred("engineer", True)

        assert agent_manager.has_pending_changes() is True

    # Test 17: has_pending_changes - False
    def test_has_pending_changes_false(self, agent_manager):
        """Test has_pending_changes when no changes exist."""
        assert agent_manager.has_pending_changes() is False

    # Test 18: discover_agents - success
    @patch("claude_mpm.cli.commands.configure.Path")
    def test_discover_agents_success(self, mock_path_class, agent_manager, tmp_path):
        """Test discovering agents from templates."""
        # Create mock templates directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create sample templates
        (templates_dir / "engineer.json").write_text(
            json.dumps({"name": "Engineer", "role": "Developer"})
        )
        (templates_dir / "designer.json").write_text(
            json.dumps({"name": "Designer", "role": "UI Designer"})
        )

        # Mock Path to return our templates dir
        agent_manager.templates_dir = templates_dir

        agents = agent_manager.discover_agents()

        assert len(agents) == 2
        agent_names = [a.name for a in agents]
        assert "engineer" in agent_names
        assert "designer" in agent_names

    # Test 19: discover_agents - empty directory
    def test_discover_agents_empty(self, agent_manager, tmp_path):
        """Test discovering agents from empty directory."""
        templates_dir = tmp_path / "empty_templates"
        templates_dir.mkdir()
        agent_manager.templates_dir = templates_dir

        agents = agent_manager.discover_agents()

        # Should return default agent
        assert len(agents) == 1
        assert agents[0].name == "engineer"
        assert "No agents found" in agents[0].description


# ==============================================================================
# ConfigureCommand Unit Tests
# ==============================================================================


class TestConfigureCommand:
    """Unit tests for ConfigureCommand class."""

    @pytest.fixture
    def configure_cmd(self):
        """Create ConfigureCommand instance."""
        return ConfigureCommand()

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary configuration directory."""
        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    # Test 20: __init__
    def test_init(self):
        """Test ConfigureCommand initialization."""
        cmd = ConfigureCommand()

        # ConfigureCommand constructor passes "configure" to BaseCommand
        assert cmd.current_scope == "project"
        assert cmd.project_dir == Path.cwd()
        assert cmd.agent_manager is None
        assert isinstance(cmd.console, Console)

    # Test 21: validate_args - valid
    def test_validate_args_valid(self, configure_cmd):
        """Test validate_args with valid arguments."""
        args = Namespace(
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
            version_info=False,
            enable_agent=None,
            disable_agent=None,
        )

        error = configure_cmd.validate_args(args)

        assert error is None

    # Test 22: validate_args - conflicting nav options
    def test_validate_args_conflicting_nav(self, configure_cmd):
        """Test validate_args with conflicting navigation options."""
        args = Namespace(
            agents=True,
            templates=True,
            behaviors=False,
            startup=False,
            version_info=False,
            enable_agent=None,
            disable_agent=None,
        )

        error = configure_cmd.validate_args(args)

        assert error is not None
        assert "Only one direct navigation option" in error

    # Test 23: validate_args - conflicting enable/disable
    def test_validate_args_conflicting_enable_disable(self, configure_cmd):
        """Test validate_args with both enable and disable."""
        args = Namespace(
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
            version_info=False,
            enable_agent="engineer",
            disable_agent="designer",
        )

        error = configure_cmd.validate_args(args)

        assert error is not None
        assert "Cannot enable and disable" in error

    # Test 24: run - list agents
    def test_run_list_agents(self, configure_cmd):
        """Test run with --list-agents flag."""
        args = Namespace(
            scope="project",
            project_dir=None,
            no_colors=False,
            list_agents=True,
            enable_agent=None,
            disable_agent=None,
            export_config=None,
            import_config=None,
            version_info=False,
            install_hooks=False,
            verify_hooks=False,
            uninstall_hooks=False,
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
        )

        with patch.object(
            configure_cmd, "_list_agents_non_interactive"
        ) as mock_list:
            mock_list.return_value = CommandResult.success_result()
            result = configure_cmd.run(args)

        mock_list.assert_called_once()
        assert result.success is True

    # Test 25: run - enable agent
    def test_run_enable_agent(self, configure_cmd):
        """Test run with --enable-agent flag."""
        args = Namespace(
            scope="project",
            project_dir=None,
            no_colors=False,
            list_agents=False,
            enable_agent="engineer",
            disable_agent=None,
            export_config=None,
            import_config=None,
            version_info=False,
            install_hooks=False,
            verify_hooks=False,
            uninstall_hooks=False,
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
        )

        with patch.object(
            configure_cmd, "_enable_agent_non_interactive"
        ) as mock_enable:
            mock_enable.return_value = CommandResult.success_result()
            result = configure_cmd.run(args)

        mock_enable.assert_called_once_with("engineer")
        assert result.success is True

    # Test 26: run - disable agent
    def test_run_disable_agent(self, configure_cmd):
        """Test run with --disable-agent flag."""
        args = Namespace(
            scope="project",
            project_dir=None,
            no_colors=False,
            list_agents=False,
            enable_agent=None,
            disable_agent="designer",
            export_config=None,
            import_config=None,
            version_info=False,
            install_hooks=False,
            verify_hooks=False,
            uninstall_hooks=False,
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
        )

        with patch.object(
            configure_cmd, "_disable_agent_non_interactive"
        ) as mock_disable:
            mock_disable.return_value = CommandResult.success_result()
            result = configure_cmd.run(args)

        mock_disable.assert_called_once_with("designer")
        assert result.success is True

    # Test 27: run - export config
    def test_run_export_config(self, configure_cmd):
        """Test run with --export-config flag."""
        args = Namespace(
            scope="project",
            project_dir=None,
            no_colors=False,
            list_agents=False,
            enable_agent=None,
            disable_agent=None,
            export_config="/tmp/config.json",
            import_config=None,
            version_info=False,
            install_hooks=False,
            verify_hooks=False,
            uninstall_hooks=False,
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
        )

        with patch.object(configure_cmd, "_export_config") as mock_export:
            mock_export.return_value = CommandResult.success_result()
            result = configure_cmd.run(args)

        mock_export.assert_called_once_with("/tmp/config.json")
        assert result.success is True

    # Test 28: run - import config
    def test_run_import_config(self, configure_cmd):
        """Test run with --import-config flag."""
        args = Namespace(
            scope="project",
            project_dir=None,
            no_colors=False,
            list_agents=False,
            enable_agent=None,
            disable_agent=None,
            export_config=None,
            import_config="/tmp/config.json",
            version_info=False,
            install_hooks=False,
            verify_hooks=False,
            uninstall_hooks=False,
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
        )

        with patch.object(configure_cmd, "_import_config") as mock_import:
            mock_import.return_value = CommandResult.success_result()
            result = configure_cmd.run(args)

        mock_import.assert_called_once_with("/tmp/config.json")
        assert result.success is True

    # Test 29: run - version info
    def test_run_version_info(self, configure_cmd):
        """Test run with --version-info flag."""
        args = Namespace(
            scope="project",
            project_dir=None,
            no_colors=False,
            list_agents=False,
            enable_agent=None,
            disable_agent=None,
            export_config=None,
            import_config=None,
            version_info=True,
            install_hooks=False,
            verify_hooks=False,
            uninstall_hooks=False,
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
        )

        with patch.object(configure_cmd, "_show_version_info") as mock_version:
            mock_version.return_value = CommandResult.success_result()
            result = configure_cmd.run(args)

        mock_version.assert_called_once()
        assert result.success is True

    # Test 30: run - install hooks
    def test_run_install_hooks(self, configure_cmd):
        """Test run with --install-hooks flag."""
        args = Namespace(
            scope="project",
            project_dir=None,
            no_colors=False,
            list_agents=False,
            enable_agent=None,
            disable_agent=None,
            export_config=None,
            import_config=None,
            version_info=False,
            install_hooks=True,
            force=False,
            verify_hooks=False,
            uninstall_hooks=False,
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
        )

        with patch.object(configure_cmd, "_install_hooks") as mock_install:
            mock_install.return_value = CommandResult.success_result()
            result = configure_cmd.run(args)

        mock_install.assert_called_once_with(force=False)
        assert result.success is True

    # Test 31: run - scope setting project
    def test_run_scope_project(self, configure_cmd, tmp_path):
        """Test run with project scope."""
        args = Namespace(
            scope="project",
            project_dir=str(tmp_path),
            no_colors=False,
            list_agents=False,
            enable_agent=None,
            disable_agent=None,
            export_config=None,
            import_config=None,
            version_info=True,
            install_hooks=False,
            verify_hooks=False,
            uninstall_hooks=False,
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
        )

        with patch.object(configure_cmd, "_show_version_info") as mock_version:
            mock_version.return_value = CommandResult.success_result()
            configure_cmd.run(args)

        assert configure_cmd.current_scope == "project"
        assert configure_cmd.project_dir == tmp_path
        assert configure_cmd.agent_manager.config_dir == tmp_path / ".claude-mpm"

    # Test 32: run - scope setting user
    def test_run_scope_user(self, configure_cmd):
        """Test run with user scope."""
        args = Namespace(
            scope="user",
            project_dir=None,
            no_colors=False,
            list_agents=False,
            enable_agent=None,
            disable_agent=None,
            export_config=None,
            import_config=None,
            version_info=True,
            install_hooks=False,
            verify_hooks=False,
            uninstall_hooks=False,
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
        )

        with patch.object(configure_cmd, "_show_version_info") as mock_version:
            mock_version.return_value = CommandResult.success_result()
            configure_cmd.run(args)

        assert configure_cmd.current_scope == "user"
        expected_config_dir = Path.home() / ".claude-mpm"
        assert configure_cmd.agent_manager.config_dir == expected_config_dir

    # Test 33: run - no colors
    def test_run_no_colors(self, configure_cmd):
        """Test run with --no-colors flag."""
        args = Namespace(
            scope="project",
            project_dir=None,
            no_colors=True,
            list_agents=False,
            enable_agent=None,
            disable_agent=None,
            export_config=None,
            import_config=None,
            version_info=True,
            install_hooks=False,
            verify_hooks=False,
            uninstall_hooks=False,
            agents=False,
            templates=False,
            behaviors=False,
            startup=False,
        )

        with patch.object(configure_cmd, "_show_version_info") as mock_version:
            mock_version.return_value = CommandResult.success_result()
            configure_cmd.run(args)

        assert configure_cmd.console.color_system is None

    # Test 34: _list_agents_non_interactive
    def test_list_agents_non_interactive(self, configure_cmd, temp_config_dir):
        """Test _list_agents_non_interactive method."""
        configure_cmd.agent_manager = SimpleAgentManager(temp_config_dir)

        with patch.object(configure_cmd, "console"):
            with patch.object(
                configure_cmd.agent_manager, "discover_agents"
            ) as mock_discover:
                mock_discover.return_value = [
                    AgentConfig("engineer", "Software Engineer", []),
                    AgentConfig("designer", "UI Designer", []),
                ]
                result = configure_cmd._list_agents_non_interactive()

        assert result.success is True
        mock_discover.assert_called_once()

    # Test 35: _enable_agent_non_interactive - success
    def test_enable_agent_non_interactive_success(
        self, configure_cmd, temp_config_dir
    ):
        """Test enabling agent in non-interactive mode."""
        configure_cmd.agent_manager = SimpleAgentManager(temp_config_dir)

        result = configure_cmd._enable_agent_non_interactive("engineer")

        assert result.success is True
        assert configure_cmd.agent_manager.is_agent_enabled("engineer") is True

    # Test 36: _disable_agent_non_interactive - success
    def test_disable_agent_non_interactive_success(
        self, configure_cmd, temp_config_dir
    ):
        """Test disabling agent in non-interactive mode."""
        configure_cmd.agent_manager = SimpleAgentManager(temp_config_dir)

        result = configure_cmd._disable_agent_non_interactive("designer")

        assert result.success is True
        assert configure_cmd.agent_manager.is_agent_enabled("designer") is False

    # Test 37: _show_version_info
    @patch("subprocess.run")
    def test_show_version_info(self, mock_subprocess_run, configure_cmd):
        """Test showing version info."""
        # Mock subprocess.run for Claude version check (imported inside method)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Claude Code v1.0.0"
        mock_subprocess_run.return_value = mock_result

        with patch.object(configure_cmd.console, "print"):
            result = configure_cmd._show_version_info()

        assert result.success is True
        assert "mpm_version" in result.data
        assert "build_number" in result.data
        assert "python_version" in result.data


# ==============================================================================
# Additional Method Tests (targeting 85%+ coverage)
# ==============================================================================


class TestConfigureCommandAdditionalMethods:
    """Additional unit tests for remaining ConfigureCommand methods."""

    @pytest.fixture
    def configure_cmd(self):
        """Create ConfigureCommand instance."""
        return ConfigureCommand()

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary configuration directory."""
        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    # Test 38: _parse_id_selection - single id
    def test_parse_id_selection_single(self, configure_cmd):
        """Test parsing single ID selection."""
        ids = configure_cmd._parse_id_selection("5", max_id=10)
        assert ids == [5]

    # Test 39: _parse_id_selection - range
    def test_parse_id_selection_range(self, configure_cmd):
        """Test parsing range selection."""
        ids = configure_cmd._parse_id_selection("3-6", max_id=10)
        assert ids == [3, 4, 5, 6]

    # Test 40: _parse_id_selection - comma separated
    def test_parse_id_selection_comma(self, configure_cmd):
        """Test parsing comma-separated selection."""
        ids = configure_cmd._parse_id_selection("2,5,8", max_id=10)
        assert ids == [2, 5, 8]

    # Test 41: _parse_id_selection - mixed
    def test_parse_id_selection_mixed(self, configure_cmd):
        """Test parsing mixed selection."""
        ids = configure_cmd._parse_id_selection("1,3-5,8", max_id=10)
        assert sorted(ids) == [1, 3, 4, 5, 8]

    # Test 42: _parse_id_selection - invalid
    def test_parse_id_selection_invalid(self, configure_cmd):
        """Test parsing invalid selection raises ValueError."""
        with pytest.raises(ValueError):
            configure_cmd._parse_id_selection("invalid", max_id=10)

    # Test 43: _parse_id_selection - out of range
    def test_parse_id_selection_out_of_range(self, configure_cmd):
        """Test parsing out of range IDs raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ID"):
            configure_cmd._parse_id_selection("5,15,20", max_id=10)

    # Test 44: _display_header
    def test_display_header(self, configure_cmd):
        """Test _display_header method."""
        with patch.object(configure_cmd.console, "print") as mock_print:
            configure_cmd._display_header()

        # Should print header
        assert mock_print.called

    # Test 45: _get_agent_template_path - project level exists
    def test_get_agent_template_path_project(self, configure_cmd, tmp_path, temp_config_dir):
        """Test getting agent template path from project level."""
        configure_cmd.project_dir = tmp_path
        configure_cmd.current_scope = "project"
        configure_cmd.agent_manager = SimpleAgentManager(temp_config_dir)

        # Create custom template in project config
        custom_dir = tmp_path / ".claude-mpm" / "agents"
        custom_dir.mkdir(parents=True)
        template_file = custom_dir / "engineer.json"
        template_file.write_text("{}")

        path = configure_cmd._get_agent_template_path("engineer")

        assert path == template_file

    # Test 46: _get_agent_template_path - user level fallback
    def test_get_agent_template_path_user(self, configure_cmd, tmp_path, temp_config_dir):
        """Test getting agent template path from user level."""
        configure_cmd.project_dir = tmp_path
        configure_cmd.current_scope = "user"
        configure_cmd.agent_manager = SimpleAgentManager(temp_config_dir)

        with patch("claude_mpm.cli.commands.configure.Path.home") as mock_home:
            user_dir = tmp_path / "user_home"
            mock_home.return_value = user_dir
            user_agent_dir = user_dir / ".claude-mpm" / "agents"
            user_agent_dir.mkdir(parents=True)
            template_file = user_agent_dir / "designer.json"
            template_file.write_text("{}")

            path = configure_cmd._get_agent_template_path("designer")

            assert path == template_file

    # Test 47: _get_agent_template_path - default fallback
    def test_get_agent_template_path_default(self, configure_cmd, tmp_path, temp_config_dir):
        """Test getting agent template path from default location."""
        configure_cmd.project_dir = tmp_path
        configure_cmd.current_scope = "project"
        configure_cmd.agent_manager = SimpleAgentManager(temp_config_dir)

        # Create templates dir for agent manager
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        configure_cmd.agent_manager.templates_dir = templates_dir

        # Create system template
        system_template = templates_dir / "qa.json"
        system_template.write_text("{}")

        path = configure_cmd._get_agent_template_path("qa")

        # Should return system template path
        assert path == system_template
