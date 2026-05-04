"""Tests for .mcp.json rollback semantics in `claude-mpm setup`.

Regression coverage for issue #493: when an MCP-server setup writes a new
entry into ``.mcp.json`` and a downstream auth/validation step fails, the
file must be restored to its previous state (or removed entirely on a
fresh install).
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.cli.commands.setup import (
    AuthFailedError,
    SetupCommand,
    _mcp_config_transaction,
    _read_mcp_json_snapshot,
    _restore_mcp_json,
)


@pytest.fixture
def temp_project_dir():
    """Provide a clean temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ---------------------------------------------------------------------------
# Snapshot / restore helpers
# ---------------------------------------------------------------------------


class TestSnapshotAndRestore:
    """Direct coverage of the snapshot/restore primitives."""

    def test_snapshot_returns_none_when_file_missing(self, temp_project_dir):
        snapshot = _read_mcp_json_snapshot(temp_project_dir / ".mcp.json")
        assert snapshot is None

    def test_snapshot_returns_raw_contents(self, temp_project_dir):
        path = temp_project_dir / ".mcp.json"
        path.write_text('{"mcpServers": {"foo": {"command": "foo"}}}\n')
        snapshot = _read_mcp_json_snapshot(path)
        assert snapshot == '{"mcpServers": {"foo": {"command": "foo"}}}\n'

    def test_restore_recreates_file_from_snapshot(self, temp_project_dir):
        path = temp_project_dir / ".mcp.json"
        path.write_text("original\n")
        snapshot = _read_mcp_json_snapshot(path)

        # Simulate a write that we want to undo.
        path.write_text("corrupted\n")
        _restore_mcp_json(path, snapshot)

        assert path.read_text() == "original\n"

    def test_restore_deletes_file_when_no_prior_snapshot(self, temp_project_dir):
        path = temp_project_dir / ".mcp.json"
        # Snapshot taken before file existed.
        snapshot = _read_mcp_json_snapshot(path)
        assert snapshot is None

        # Something later created the file.
        path.write_text('{"mcpServers": {"foo": {}}}')
        assert path.exists()

        _restore_mcp_json(path, snapshot)
        assert not path.exists()


# ---------------------------------------------------------------------------
# Context manager behaviour
# ---------------------------------------------------------------------------


class TestMcpConfigTransaction:
    """Behavioural tests for `_mcp_config_transaction`."""

    def test_success_persists_changes(self, temp_project_dir):
        path = temp_project_dir / ".mcp.json"
        path.write_text('{"mcpServers": {}}\n')

        with _mcp_config_transaction(temp_project_dir):
            path.write_text('{"mcpServers": {"new": {"command": "new"}}}\n')

        # Block exited normally — new contents must remain.
        data = json.loads(path.read_text())
        assert data == {"mcpServers": {"new": {"command": "new"}}}

    def test_failure_restores_previous_state(self, temp_project_dir):
        path = temp_project_dir / ".mcp.json"
        original = '{"mcpServers": {"existing": {"command": "existing"}}}\n'
        path.write_text(original)

        with pytest.raises(AuthFailedError):
            with _mcp_config_transaction(temp_project_dir):
                # Simulate write of new entry.
                path.write_text(
                    '{"mcpServers": {"existing": {"command": "existing"}, '
                    '"new": {"command": "new"}}}\n'
                )
                # Simulate auth failure after the write.
                raise AuthFailedError("port conflict")

        # File must be exactly as before.
        assert path.read_text() == original

    def test_failure_on_fresh_install_removes_file(self, temp_project_dir):
        path = temp_project_dir / ".mcp.json"
        assert not path.exists()

        with pytest.raises(AuthFailedError):
            with _mcp_config_transaction(temp_project_dir):
                # Setup creates the file…
                path.write_text('{"mcpServers": {"new": {"command": "new"}}}\n')
                # …but auth then fails.
                raise AuthFailedError("port conflict")

        # No prior file — rollback must delete the partial write.
        assert not path.exists()

    def test_rollback_message_emitted_on_failure(self, temp_project_dir, capsys):
        path = temp_project_dir / ".mcp.json"
        path.write_text('{"mcpServers": {}}\n')

        with pytest.raises(AuthFailedError):
            with _mcp_config_transaction(temp_project_dir):
                path.write_text('{"mcpServers": {"x": {}}}\n')
                raise AuthFailedError("boom")

        out = capsys.readouterr().out
        assert "rolled back .mcp.json" in out.lower()


# ---------------------------------------------------------------------------
# End-to-end behaviour for `_setup_google_workspace`
# ---------------------------------------------------------------------------


def _write_existing_mcp_json(project_dir: Path) -> str:
    """Helper: create an existing .mcp.json with one unrelated entry."""
    payload = '{\n  "mcpServers": {\n    "other": {\n      "command": "other"\n    }\n  }\n}\n'
    (project_dir / ".mcp.json").write_text(payload)
    return payload


class TestGoogleWorkspaceSetupRollback:
    """Verify that gworkspace-mcp setup honours rollback on auth failure."""

    @patch("claude_mpm.cli.commands.setup.subprocess.run")
    @patch("claude_mpm.services.package_installer.PackageInstallerService")
    @patch("claude_mpm.cli.commands.setup.Path.cwd")
    def test_auth_failure_rolls_back_existing_config(
        self,
        mock_cwd,
        mock_installer_cls,
        mock_subprocess,
        temp_project_dir,
    ):
        """Auth failure must restore .mcp.json to its previous contents."""
        mock_cwd.return_value = temp_project_dir

        # Pretend the package is already installed so we skip install.
        installer = mock_installer_cls.return_value
        installer.is_installed.return_value = True

        # gworkspace-mcp setup exits non-zero (e.g. port conflict).
        mock_subprocess.return_value.returncode = 1

        # Pre-existing .mcp.json that must survive the failed run.
        original = _write_existing_mcp_json(temp_project_dir)

        # Provide credentials so the OAuth path actually runs.
        with patch(
            "claude_mpm.cli.commands.oauth._detect_google_credentials",
            return_value=("client-id", "client-secret", "env"),
        ):
            cmd = SetupCommand()
            args = type("A", (), {"force": False, "upgrade": False})()
            result = cmd._setup_google_workspace(args)

        assert not result.success
        # File must be byte-identical to the original.
        assert (temp_project_dir / ".mcp.json").read_text() == original

    @patch("claude_mpm.cli.commands.setup.subprocess.run")
    @patch("claude_mpm.services.package_installer.PackageInstallerService")
    @patch("claude_mpm.cli.commands.setup.Path.cwd")
    def test_auth_failure_on_fresh_install_removes_file(
        self,
        mock_cwd,
        mock_installer_cls,
        mock_subprocess,
        temp_project_dir,
    ):
        """When .mcp.json did not exist, rollback must delete any partial write."""
        mock_cwd.return_value = temp_project_dir

        installer = mock_installer_cls.return_value
        installer.is_installed.return_value = True

        mock_subprocess.return_value.returncode = 1  # auth fails

        with patch(
            "claude_mpm.cli.commands.oauth._detect_google_credentials",
            return_value=("client-id", "client-secret", "env"),
        ):
            cmd = SetupCommand()
            args = type("A", (), {"force": False, "upgrade": False})()
            result = cmd._setup_google_workspace(args)

        assert not result.success
        # No prior file — none must exist now.
        assert not (temp_project_dir / ".mcp.json").exists()

    @patch("claude_mpm.cli.commands.setup.subprocess.run")
    @patch("claude_mpm.services.package_installer.PackageInstallerService")
    @patch("claude_mpm.cli.commands.setup.Path.cwd")
    def test_auth_success_persists_config(
        self,
        mock_cwd,
        mock_installer_cls,
        mock_subprocess,
        temp_project_dir,
    ):
        """When auth succeeds, the new gworkspace-mcp entry must persist."""
        mock_cwd.return_value = temp_project_dir

        installer = mock_installer_cls.return_value
        installer.is_installed.return_value = True

        # `gworkspace-mcp setup` succeeds; subsequent `gworkspace-mcp --help`
        # call (for registry) is also fine.
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "help text"

        with (
            patch(
                "claude_mpm.cli.commands.oauth._detect_google_credentials",
                return_value=("client-id", "client-secret", "env"),
            ),
            patch("claude_mpm.services.setup_registry.SetupRegistry"),
        ):
            cmd = SetupCommand()
            args = type("A", (), {"force": False, "upgrade": False})()
            result = cmd._setup_google_workspace(args)

        assert result.success
        mcp_path = temp_project_dir / ".mcp.json"
        assert mcp_path.exists()
        data = json.loads(mcp_path.read_text())
        assert "gworkspace-mcp" in data.get("mcpServers", {})
