"""Tests for SDKCommandRouter slash command handling in SDK mode."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.core.sdk_command_router import CommandResult, SDKCommandRouter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock ClaudeSDKClient with stub methods."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_tracker() -> MagicMock:
    """Mock SessionStateTracker."""
    tracker = MagicMock()
    tracker.get_session_state.return_value = {
        "model": "claude-sonnet-4-20250514",
        "total_cost_usd": 0.0042,
        "turn_count": 7,
    }
    return tracker


@pytest.fixture
def router(mock_client: MagicMock, mock_tracker: MagicMock) -> SDKCommandRouter:
    """Router with both client and tracker wired up."""
    return SDKCommandRouter(client=mock_client, tracker=mock_tracker)


@pytest.fixture
def router_no_tracker(mock_client: MagicMock) -> SDKCommandRouter:
    """Router with client but no tracker."""
    return SDKCommandRouter(client=mock_client, tracker=None)


@pytest.fixture
def router_no_client(mock_tracker: MagicMock) -> SDKCommandRouter:
    """Router with tracker but no client."""
    return SDKCommandRouter(client=None, tracker=mock_tracker)


# ---------------------------------------------------------------------------
# 1. Non-slash input passes through
# ---------------------------------------------------------------------------


class TestNonSlashPassthrough:
    def test_non_slash_not_handled(self, router: SDKCommandRouter) -> None:
        result = router.route("hello world")
        assert result.handled is False

    def test_empty_string_not_handled(self, router: SDKCommandRouter) -> None:
        result = router.route("")
        assert result.handled is False

    def test_plain_text_not_handled(self, router: SDKCommandRouter) -> None:
        result = router.route("tell me about python")
        assert result.handled is False


# ---------------------------------------------------------------------------
# 2. Exit / quit
# ---------------------------------------------------------------------------


class TestExitCommands:
    def test_exit_command(self, router: SDKCommandRouter) -> None:
        result = router.route("/exit")
        assert result.handled is True
        assert result.should_exit is True
        assert result.output is not None

    def test_quit_command(self, router: SDKCommandRouter) -> None:
        result = router.route("/quit")
        assert result.handled is True
        assert result.should_exit is True

    def test_exit_with_whitespace(self, router: SDKCommandRouter) -> None:
        result = router.route("  /exit  ")
        assert result.handled is True
        assert result.should_exit is True


# ---------------------------------------------------------------------------
# 3. Help
# ---------------------------------------------------------------------------


class TestHelpCommand:
    def test_help_command(self, router: SDKCommandRouter) -> None:
        result = router.route("/help")
        assert result.handled is True
        assert result.output is not None
        assert "SDK Mode Commands" in result.output
        assert "/exit" in result.output
        assert "/cost" in result.output

    def test_help_mentions_repl_only(self, router: SDKCommandRouter) -> None:
        result = router.route("/help")
        assert "REPL-only" in (result.output or "")


# ---------------------------------------------------------------------------
# 4. Cost
# ---------------------------------------------------------------------------


class TestCostCommand:
    def test_cost_with_tracker(
        self, router: SDKCommandRouter, mock_tracker: MagicMock
    ) -> None:
        result = router.route("/cost")
        assert result.handled is True
        assert "$0.0042" in (result.output or "")
        assert "7 turns" in (result.output or "")

    def test_cost_without_tracker(self, router_no_tracker: SDKCommandRouter) -> None:
        result = router_no_tracker.route("/cost")
        assert result.handled is True
        assert "not available" in (result.output or "").lower()

    def test_cost_no_cost_yet(
        self, router: SDKCommandRouter, mock_tracker: MagicMock
    ) -> None:
        mock_tracker.get_session_state.return_value = {
            "total_cost_usd": None,
            "turn_count": 3,
        }
        result = router.route("/cost")
        assert result.handled is True
        assert "3 turns" in (result.output or "")
        assert "not yet reported" in (result.output or "")


# ---------------------------------------------------------------------------
# 5. Model
# ---------------------------------------------------------------------------


class TestModelCommand:
    def test_model_show(
        self, router: SDKCommandRouter, mock_tracker: MagicMock
    ) -> None:
        result = router.route("/model")
        assert result.handled is True
        assert "claude-sonnet-4-20250514" in (result.output or "")

    def test_model_set(self, router: SDKCommandRouter, mock_client: MagicMock) -> None:
        result = router.route("/model sonnet")
        assert result.handled is True
        mock_client.set_model.assert_called_once_with("sonnet")
        assert "sonnet" in (result.output or "")

    def test_model_set_failure(
        self, router: SDKCommandRouter, mock_client: MagicMock
    ) -> None:
        mock_client.set_model.side_effect = AttributeError("not supported")
        result = router.route("/model opus")
        assert result.handled is True
        assert "Failed" in (result.output or "")

    def test_model_no_client(self, router_no_client: SDKCommandRouter) -> None:
        """When no client, /model with args is not handled (passthrough)."""
        result = router_no_client.route("/model sonnet")
        assert result.handled is False


# ---------------------------------------------------------------------------
# 6. Permissions
# ---------------------------------------------------------------------------


class TestPermissionsCommand:
    def test_permissions_set(
        self, router: SDKCommandRouter, mock_client: MagicMock
    ) -> None:
        result = router.route("/permissions bypassPermissions")
        assert result.handled is True
        mock_client.set_permission_mode.assert_called_once_with("bypassPermissions")
        assert "bypassPermissions" in (result.output or "")

    def test_permissions_no_args(self, router: SDKCommandRouter) -> None:
        result = router.route("/permissions")
        assert result.handled is True
        assert "Use:" in (result.output or "")

    def test_permissions_failure(
        self, router: SDKCommandRouter, mock_client: MagicMock
    ) -> None:
        mock_client.set_permission_mode.side_effect = Exception("denied")
        result = router.route("/permissions x")
        assert result.handled is True
        assert "Failed" in (result.output or "")


# ---------------------------------------------------------------------------
# 7. MCP
# ---------------------------------------------------------------------------


class TestMCPCommand:
    def test_mcp_status(self, router: SDKCommandRouter, mock_client: MagicMock) -> None:
        srv = MagicMock()
        srv.name = "filesystem"
        srv.status = "connected"
        status_obj = MagicMock()
        status_obj.servers = [srv]
        mock_client.get_mcp_status.return_value = status_obj

        result = router.route("/mcp")
        assert result.handled is True
        assert "filesystem" in (result.output or "")
        assert "connected" in (result.output or "")

    def test_mcp_no_servers(
        self, router: SDKCommandRouter, mock_client: MagicMock
    ) -> None:
        status_obj = MagicMock()
        status_obj.servers = []
        mock_client.get_mcp_status.return_value = status_obj

        result = router.route("/mcp")
        assert result.handled is True
        assert "none configured" in (result.output or "")

    def test_mcp_error(self, router: SDKCommandRouter, mock_client: MagicMock) -> None:
        mock_client.get_mcp_status.side_effect = RuntimeError("unavailable")
        result = router.route("/mcp")
        assert result.handled is True
        assert "error" in (result.output or "").lower()


# ---------------------------------------------------------------------------
# 8. External CLI commands (subprocess)
# ---------------------------------------------------------------------------


class TestExternalCommands:
    @patch("claude_mpm.core.sdk_command_router.subprocess.run")
    def test_login_runs_subprocess(
        self, mock_run: MagicMock, router: SDKCommandRouter
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        result = router.route("/login")
        assert result.handled is True
        mock_run.assert_called_once()
        args_used = mock_run.call_args[0][0]
        assert args_used == ["claude", "auth", "login"]
        assert "successfully" in (result.output or "")

    @patch("claude_mpm.core.sdk_command_router.subprocess.run")
    def test_doctor_runs_subprocess(
        self, mock_run: MagicMock, router: SDKCommandRouter
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        result = router.route("/doctor")
        assert result.handled is True
        args_used = mock_run.call_args[0][0]
        assert args_used == ["claude", "doctor"]

    @patch("claude_mpm.core.sdk_command_router.subprocess.run")
    def test_logout_runs_subprocess(
        self, mock_run: MagicMock, router: SDKCommandRouter
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        result = router.route("/logout")
        assert result.handled is True

    @patch("claude_mpm.core.sdk_command_router.subprocess.run")
    def test_external_command_not_found(
        self, mock_run: MagicMock, router: SDKCommandRouter
    ) -> None:
        mock_run.side_effect = FileNotFoundError()
        result = router.route("/login")
        assert result.handled is True
        assert "not found" in (result.output or "").lower()

    @patch("claude_mpm.core.sdk_command_router.subprocess.run")
    def test_external_command_nonzero_exit(
        self, mock_run: MagicMock, router: SDKCommandRouter
    ) -> None:
        mock_run.return_value = MagicMock(returncode=1)
        result = router.route("/login")
        assert result.handled is True
        assert "exited with code 1" in (result.output or "")

    @patch("claude_mpm.core.sdk_command_router.subprocess.run")
    def test_external_command_timeout(
        self, mock_run: MagicMock, router: SDKCommandRouter
    ) -> None:
        import subprocess as sp

        mock_run.side_effect = sp.TimeoutExpired(cmd="claude", timeout=120)
        result = router.route("/login")
        assert result.handled is True
        assert "timed out" in (result.output or "").lower()


# ---------------------------------------------------------------------------
# 9. Unsupported REPL-only commands
# ---------------------------------------------------------------------------


class TestUnsupportedCommands:
    def test_compact_unsupported(self, router: SDKCommandRouter) -> None:
        result = router.route("/compact")
        assert result.handled is True
        assert "REPL-only" in (result.output or "")

    def test_vim_unsupported(self, router: SDKCommandRouter) -> None:
        result = router.route("/vim")
        assert result.handled is True
        assert "REPL-only" in (result.output or "")

    def test_theme_unsupported(self, router: SDKCommandRouter) -> None:
        result = router.route("/theme")
        assert result.handled is True

    def test_terminal_setup_unsupported(self, router: SDKCommandRouter) -> None:
        result = router.route("/terminal-setup")
        assert result.handled is True
        assert "REPL-only" in (result.output or "")


# ---------------------------------------------------------------------------
# 10. Unknown slash commands pass through to LLM
# ---------------------------------------------------------------------------


class TestUnknownSlashCommands:
    def test_unknown_slash_passthrough(self, router: SDKCommandRouter) -> None:
        result = router.route("/unknown-thing")
        assert result.handled is False

    def test_unknown_slash_with_args(self, router: SDKCommandRouter) -> None:
        result = router.route("/foobar some args")
        assert result.handled is False


# ---------------------------------------------------------------------------
# 11. Clear command
# ---------------------------------------------------------------------------


class TestClearCommand:
    def test_clear_handled(self, router: SDKCommandRouter) -> None:
        result = router.route("/clear")
        assert result.handled is True
        assert result.should_exit is False
