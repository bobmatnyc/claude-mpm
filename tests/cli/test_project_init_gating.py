"""Tests for project-level .claude-mpm/ directory creation gating.

Verifies that ``initialize_project_directory()`` is only called for commands
that actually need a project workspace, and that read-only / informational
commands do NOT create a spurious ``.claude-mpm/`` directory in the cwd.

See: GitHub issue #703
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.command_config import needs_project_workspace

# ---------------------------------------------------------------------------
# Helper — build a minimal args namespace
# ---------------------------------------------------------------------------


def _args(command: str | None = None, **subcommands) -> SimpleNamespace:
    """Build a SimpleNamespace that mimics argparse output.

    Args:
        command: The top-level command string (e.g. ``"run"``, ``"monitor"``).
        **subcommands: Extra attributes such as ``monitor_command="status"``.
    """
    ns = SimpleNamespace(command=command, **subcommands)
    return ns


# ===========================================================================
# 1. Unit tests for needs_project_workspace() gate helper
# ===========================================================================


class TestNeedsProjectWorkspace:
    """Covers needs_project_workspace() for all relevant command shapes."""

    # --- Workspace commands (must return True) ------------------------------

    def test_run_needs_workspace(self):
        assert needs_project_workspace(_args("run")) is True

    def test_run_guarded_needs_workspace(self):
        assert needs_project_workspace(_args("run-guarded")) is True

    def test_tickets_needs_workspace(self):
        assert needs_project_workspace(_args("tickets")) is True

    def test_mpm_init_needs_workspace(self):
        # mpm-init is explicitly a workspace command per the issue
        assert needs_project_workspace(_args("mpm-init")) is True

    def test_aggregate_needs_workspace(self):
        assert needs_project_workspace(_args("aggregate")) is True

    def test_analyze_needs_workspace(self):
        assert needs_project_workspace(_args("analyze")) is True

    def test_analyze_code_needs_workspace(self):
        assert needs_project_workspace(_args("analyze-code")) is True

    def test_cleanup_memory_needs_workspace(self):
        assert needs_project_workspace(_args("cleanup-memory")) is True

    def test_serve_needs_workspace(self):
        assert needs_project_workspace(_args("serve")) is True

    def test_monitor_start_needs_workspace(self):
        assert (
            needs_project_workspace(_args("monitor", monitor_command="start")) is True
        )

    def test_monitor_stop_needs_workspace(self):
        assert needs_project_workspace(_args("monitor", monitor_command="stop")) is True

    def test_monitor_restart_needs_workspace(self):
        assert (
            needs_project_workspace(_args("monitor", monitor_command="restart")) is True
        )

    def test_agents_deploy_needs_workspace(self):
        assert needs_project_workspace(_args("agents", agents_command="deploy")) is True

    def test_agents_force_deploy_needs_workspace(self):
        assert (
            needs_project_workspace(_args("agents", agents_command="force-deploy"))
            is True
        )

    def test_agents_fix_needs_workspace(self):
        assert needs_project_workspace(_args("agents", agents_command="fix")) is True

    def test_agents_clean_needs_workspace(self):
        assert needs_project_workspace(_args("agents", agents_command="clean")) is True

    def test_memory_init_needs_workspace(self):
        assert needs_project_workspace(_args("memory", memory_command="init")) is True

    def test_memory_add_needs_workspace(self):
        assert needs_project_workspace(_args("memory", memory_command="add")) is True

    def test_memory_build_needs_workspace(self):
        assert needs_project_workspace(_args("memory", memory_command="build")) is True

    def test_memory_clean_needs_workspace(self):
        assert needs_project_workspace(_args("memory", memory_command="clean")) is True

    def test_memory_optimize_needs_workspace(self):
        # optimize writes to .claude-mpm/memories/ via MemoryOptimizer — not read-only
        assert (
            needs_project_workspace(_args("memory", memory_command="optimize")) is True
        )

    def test_manifest_init_needs_workspace(self):
        assert (
            needs_project_workspace(_args("manifest", manifest_command="init")) is True
        )

    def test_dashboard_start_needs_workspace(self):
        assert (
            needs_project_workspace(_args("dashboard", dashboard_command="start"))
            is True
        )

    def test_dashboard_stop_needs_workspace(self):
        assert (
            needs_project_workspace(_args("dashboard", dashboard_command="stop"))
            is True
        )

    def test_skills_deploy_needs_workspace(self):
        assert needs_project_workspace(_args("skills", skills_command="deploy")) is True

    # Bias rule: unknown subcommand should default to True
    def test_monitor_unknown_subcommand_defaults_to_workspace(self):
        assert (
            needs_project_workspace(
                _args("monitor", monitor_command="unknown-future-cmd")
            )
            is True
        )

    # Bias rule: no subcommand given — default to True
    def test_monitor_no_subcommand_defaults_to_workspace(self):
        assert needs_project_workspace(_args("monitor")) is True

    def test_agents_no_subcommand_defaults_to_workspace(self):
        assert needs_project_workspace(_args("agents")) is True

    # --- Read-only commands (must return False) -----------------------------

    def test_doctor_no_workspace(self):
        assert needs_project_workspace(_args("doctor")) is False

    def test_info_no_workspace(self):
        assert needs_project_workspace(_args("info")) is False

    def test_config_no_workspace(self):
        assert needs_project_workspace(_args("config")) is False

    def test_configure_no_workspace(self):
        assert needs_project_workspace(_args("configure")) is False

    def test_upgrade_no_workspace(self):
        assert needs_project_workspace(_args("upgrade")) is False

    def test_install_no_workspace(self):
        assert needs_project_workspace(_args("install")) is False

    def test_postmortem_no_workspace(self):
        assert needs_project_workspace(_args("postmortem")) is False

    def test_migrate_no_workspace(self):
        assert needs_project_workspace(_args("migrate")) is False

    def test_mcp_no_workspace(self):
        # "mcp" is in LIGHTWEIGHT_COMMANDS (server management)
        assert needs_project_workspace(_args("mcp")) is False

    def test_slack_no_workspace(self):
        assert needs_project_workspace(_args("slack")) is False

    def test_monitor_status_no_workspace(self):
        assert (
            needs_project_workspace(_args("monitor", monitor_command="status")) is False
        )

    def test_monitor_port_no_workspace(self):
        assert (
            needs_project_workspace(_args("monitor", monitor_command="port")) is False
        )

    def test_agents_list_no_workspace(self):
        assert needs_project_workspace(_args("agents", agents_command="list")) is False

    def test_agents_view_no_workspace(self):
        assert needs_project_workspace(_args("agents", agents_command="view")) is False

    def test_skills_list_no_workspace(self):
        assert needs_project_workspace(_args("skills", skills_command="list")) is False

    def test_memory_status_no_workspace(self):
        assert (
            needs_project_workspace(_args("memory", memory_command="status")) is False
        )

    def test_memory_show_no_workspace(self):
        assert needs_project_workspace(_args("memory", memory_command="show")) is False

    def test_memory_view_no_workspace(self):
        assert needs_project_workspace(_args("memory", memory_command="view")) is False

    def test_memory_cross_ref_no_workspace(self):
        # cross-ref is deprecated and makes no writes — read-only
        assert (
            needs_project_workspace(_args("memory", memory_command="cross-ref"))
            is False
        )

    def test_memory_route_no_workspace(self):
        # route only runs MemoryRouter.analyze_and_route which has no writes — read-only
        assert needs_project_workspace(_args("memory", memory_command="route")) is False

    def test_manifest_validate_no_workspace(self):
        assert (
            needs_project_workspace(_args("manifest", manifest_command="validate"))
            is False
        )

    def test_manifest_show_no_workspace(self):
        assert (
            needs_project_workspace(_args("manifest", manifest_command="show")) is False
        )

    def test_dashboard_status_no_workspace(self):
        assert (
            needs_project_workspace(_args("dashboard", dashboard_command="status"))
            is False
        )

    def test_dashboard_open_no_workspace(self):
        assert (
            needs_project_workspace(_args("dashboard", dashboard_command="open"))
            is False
        )

    # --- bare --version / --help (no command attribute) --------------------

    def test_no_command_attribute_no_workspace(self):
        """Bare --version / --help have no args.command — must not create dir."""
        assert needs_project_workspace(SimpleNamespace()) is False

    def test_command_none_no_workspace(self):
        assert needs_project_workspace(_args(command=None)) is False


# ===========================================================================
# 2. Unit tests for ProjectInitializer.ensure_initialized gating
# ===========================================================================


class TestEnsureInitializedGating:
    """Verify that include_project=False skips initialize_project_directory."""

    def test_include_project_false_skips_project_init(self):
        from claude_mpm.init import ProjectInitializer

        initializer = ProjectInitializer()
        with (
            patch.object(
                initializer, "initialize_user_directory", return_value=True
            ) as mock_user,
            patch.object(
                initializer, "initialize_project_directory", return_value=True
            ) as mock_project,
        ):
            result = initializer.ensure_initialized(include_project=False)

        mock_user.assert_called_once()
        mock_project.assert_not_called()
        assert result is True  # user_ok=True propagated

    def test_include_project_true_calls_both(self):
        from claude_mpm.init import ProjectInitializer

        initializer = ProjectInitializer()
        with (
            patch.object(
                initializer, "initialize_user_directory", return_value=True
            ) as mock_user,
            patch.object(
                initializer, "initialize_project_directory", return_value=True
            ) as mock_project,
        ):
            result = initializer.ensure_initialized(include_project=True)

        mock_user.assert_called_once()
        mock_project.assert_called_once()
        assert result is True

    def test_default_include_project_calls_both(self):
        """Default behavior (no arg) must still call both — no regression."""
        from claude_mpm.init import ProjectInitializer

        initializer = ProjectInitializer()
        with (
            patch.object(
                initializer, "initialize_user_directory", return_value=True
            ) as mock_user,
            patch.object(
                initializer, "initialize_project_directory", return_value=True
            ) as mock_project,
        ):
            initializer.ensure_initialized()

        mock_user.assert_called_once()
        mock_project.assert_called_once()


# ===========================================================================
# 3. Unit tests for init.ensure_directories() convenience wrapper
# ===========================================================================


class TestEnsureDirectoriesWrapper:
    """Verify the module-level ensure_directories() threads project= correctly."""

    def test_project_false_propagated(self):
        from claude_mpm import init as init_module

        mock_initializer = MagicMock()
        mock_initializer.ensure_initialized.return_value = True

        with patch.object(
            init_module, "ProjectInitializer", return_value=mock_initializer
        ):
            init_module.ensure_directories(project=False)

        mock_initializer.ensure_initialized.assert_called_once_with(
            include_project=False
        )

    def test_project_true_propagated(self):
        from claude_mpm import init as init_module

        mock_initializer = MagicMock()
        mock_initializer.ensure_initialized.return_value = True

        with patch.object(
            init_module, "ProjectInitializer", return_value=mock_initializer
        ):
            init_module.ensure_directories(project=True)

        mock_initializer.ensure_initialized.assert_called_once_with(
            include_project=True
        )

    def test_default_project_true(self):
        """Calling ensure_directories() with no args must pass include_project=True."""
        from claude_mpm import init as init_module

        mock_initializer = MagicMock()
        mock_initializer.ensure_initialized.return_value = True

        with patch.object(
            init_module, "ProjectInitializer", return_value=mock_initializer
        ):
            init_module.ensure_directories()

        mock_initializer.ensure_initialized.assert_called_once_with(
            include_project=True
        )


# ===========================================================================
# 4. Integration-style tests using tmp_path
# ===========================================================================


class TestProjectDirNotCreatedForReadOnlyCommands:
    """Integration-style: assert no .claude-mpm/ created in cwd for read-only commands."""

    def _run_ensure_directories_for_args(
        self, args: SimpleNamespace, tmp_path: Path, monkeypatch
    ) -> None:
        """Helper: change cwd to tmp_path and run ensure_directories with the gate."""
        monkeypatch.chdir(tmp_path)
        # Also set CLAUDE_MPM_USER_PWD so initialize_project_directory uses tmp_path
        monkeypatch.setenv("CLAUDE_MPM_USER_PWD", str(tmp_path))

        from claude_mpm.cli import utils as cli_utils
        from claude_mpm.cli.command_config import needs_project_workspace

        wants_project = needs_project_workspace(args)

        # Patch the user directory init so we don't actually touch ~/.claude-mpm
        with patch(
            "claude_mpm.init.ProjectInitializer.initialize_user_directory",
            return_value=True,
        ):
            cli_utils.ensure_directories(project=wants_project)

    # ---- READ-ONLY: must NOT create .claude-mpm/ --------------------------

    def test_doctor_does_not_create_project_dir(self, tmp_path, monkeypatch):
        self._run_ensure_directories_for_args(_args("doctor"), tmp_path, monkeypatch)
        assert not (tmp_path / ".claude-mpm").exists(), (
            "doctor must not create a project .claude-mpm/ directory"
        )

    def test_monitor_status_does_not_create_project_dir(self, tmp_path, monkeypatch):
        self._run_ensure_directories_for_args(
            _args("monitor", monitor_command="status"), tmp_path, monkeypatch
        )
        assert not (tmp_path / ".claude-mpm").exists(), (
            "monitor status must not create a project .claude-mpm/ directory"
        )

    def test_agents_list_does_not_create_project_dir(self, tmp_path, monkeypatch):
        self._run_ensure_directories_for_args(
            _args("agents", agents_command="list"), tmp_path, monkeypatch
        )
        assert not (tmp_path / ".claude-mpm").exists(), (
            "agents list must not create a project .claude-mpm/ directory"
        )

    def test_skills_list_does_not_create_project_dir(self, tmp_path, monkeypatch):
        self._run_ensure_directories_for_args(
            _args("skills", skills_command="list"), tmp_path, monkeypatch
        )
        assert not (tmp_path / ".claude-mpm").exists()

    def test_version_does_not_create_project_dir(self, tmp_path, monkeypatch):
        """Bare --version invocation (no command attribute) must not create dir."""
        self._run_ensure_directories_for_args(SimpleNamespace(), tmp_path, monkeypatch)
        assert not (tmp_path / ".claude-mpm").exists()

    def test_manifest_validate_does_not_create_project_dir(self, tmp_path, monkeypatch):
        self._run_ensure_directories_for_args(
            _args("manifest", manifest_command="validate"), tmp_path, monkeypatch
        )
        assert not (tmp_path / ".claude-mpm").exists()

    def test_memory_status_does_not_create_project_dir(self, tmp_path, monkeypatch):
        self._run_ensure_directories_for_args(
            _args("memory", memory_command="status"), tmp_path, monkeypatch
        )
        assert not (tmp_path / ".claude-mpm").exists()

    def test_dashboard_status_does_not_create_project_dir(self, tmp_path, monkeypatch):
        self._run_ensure_directories_for_args(
            _args("dashboard", dashboard_command="status"), tmp_path, monkeypatch
        )
        assert not (tmp_path / ".claude-mpm").exists()

    # ---- WORKSPACE: MUST create .claude-mpm/ ------------------------------

    def test_run_creates_project_dir(self, tmp_path, monkeypatch):
        self._run_ensure_directories_for_args(_args("run"), tmp_path, monkeypatch)
        assert (tmp_path / ".claude-mpm").exists(), (
            "run must create a project .claude-mpm/ directory"
        )

    def test_mpm_init_creates_project_dir(self, tmp_path, monkeypatch):
        self._run_ensure_directories_for_args(_args("mpm-init"), tmp_path, monkeypatch)
        assert (tmp_path / ".claude-mpm").exists(), (
            "mpm-init must create a project .claude-mpm/ directory"
        )

    def test_monitor_start_creates_project_dir(self, tmp_path, monkeypatch):
        self._run_ensure_directories_for_args(
            _args("monitor", monitor_command="start"), tmp_path, monkeypatch
        )
        assert (tmp_path / ".claude-mpm").exists(), (
            "monitor start must create a project .claude-mpm/ directory"
        )

    # ---- USER DIR init still runs for read-only commands ------------------

    def test_user_dir_init_still_runs_for_doctor(self, tmp_path, monkeypatch):
        """Even for read-only commands, initialize_user_directory must be called."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLAUDE_MPM_USER_PWD", str(tmp_path))

        from claude_mpm.init import ProjectInitializer

        with (
            patch.object(
                ProjectInitializer,
                "initialize_user_directory",
                return_value=True,
            ) as mock_user,
            patch.object(
                ProjectInitializer,
                "initialize_project_directory",
                return_value=True,
            ) as mock_project,
        ):
            from claude_mpm import init as init_module

            init_module.ensure_directories(project=False)

        mock_user.assert_called_once()
        mock_project.assert_not_called()
