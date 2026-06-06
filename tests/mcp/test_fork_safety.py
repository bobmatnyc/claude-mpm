"""Tests for the MCP fork-safety helpers.

WHAT: Verifies that get_mp_context() and ensure_spawn_on_darwin() behave
correctly on Darwin and non-Darwin platforms, and that the spawn guard is
wired into the serve entrypoints.

WHY: These helpers prevent EXC_BAD_ACCESS / SIGSEGV on macOS (issue #690)
by ensuring MCP worker processes use the "spawn" multiprocessing start method
instead of "fork".  The tests use monkeypatching to simulate both platforms
without actually forking processes or touching user settings.
"""

from __future__ import annotations

import importlib
import multiprocessing
import sys
from unittest.mock import MagicMock, patch

import pytest  # noqa: TC002

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reload_fork_safety(monkeypatch: pytest.MonkeyPatch, platform: str):
    """Return a freshly-loaded fork_safety module with sys.platform overridden."""
    import claude_mpm.mcp.fork_safety as mod

    monkeypatch.setattr(sys, "platform", platform)
    importlib.reload(mod)
    return mod


# ---------------------------------------------------------------------------
# get_mp_context()
# ---------------------------------------------------------------------------


class TestGetMpContext:
    """Tests for get_mp_context()."""

    def test_returns_spawn_context_on_darwin(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_mp_context() returns a 'spawn' context on macOS."""
        fs = _reload_fork_safety(monkeypatch, "darwin")
        ctx = fs.get_mp_context()
        assert ctx.get_start_method() == "spawn"

    def test_returns_default_context_on_linux(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_mp_context() returns the platform default on Linux, not forced spawn."""
        fs = _reload_fork_safety(monkeypatch, "linux")
        ctx = fs.get_mp_context()
        # Must equal the real default for this process (not hard-coded "spawn").
        default = multiprocessing.get_start_method()
        assert ctx.get_start_method() == default

    def test_returns_default_context_on_win32(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_mp_context() returns the platform default on Windows."""
        fs = _reload_fork_safety(monkeypatch, "win32")
        ctx = fs.get_mp_context()
        default = multiprocessing.get_start_method()
        assert ctx.get_start_method() == default

    def test_darwin_context_exposes_process_class(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The Darwin context must expose a usable Process class."""
        fs = _reload_fork_safety(monkeypatch, "darwin")
        ctx = fs.get_mp_context()
        assert hasattr(ctx, "Process"), "spawn context must expose a Process class"


# ---------------------------------------------------------------------------
# ensure_spawn_on_darwin()
# ---------------------------------------------------------------------------


class TestEnsureSpawnOnDarwin:
    """Tests for ensure_spawn_on_darwin()."""

    def test_no_op_on_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ensure_spawn_on_darwin() is a no-op on non-Darwin platforms."""
        fs = _reload_fork_safety(monkeypatch, "linux")
        with patch("multiprocessing.set_start_method") as mock_set:
            fs.ensure_spawn_on_darwin()
        mock_set.assert_not_called()

    def test_no_op_on_win32(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ensure_spawn_on_darwin() is a no-op on Windows."""
        fs = _reload_fork_safety(monkeypatch, "win32")
        with patch("multiprocessing.set_start_method") as mock_set:
            fs.ensure_spawn_on_darwin()
        mock_set.assert_not_called()

    def test_sets_spawn_on_darwin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ensure_spawn_on_darwin() calls set_start_method('spawn', force=False)."""
        fs = _reload_fork_safety(monkeypatch, "darwin")
        with patch("multiprocessing.set_start_method") as mock_set:
            fs.ensure_spawn_on_darwin()
        mock_set.assert_called_once_with("spawn", force=False)

    def test_swallows_runtime_error_when_already_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ensure_spawn_on_darwin() silently swallows RuntimeError (already set)."""
        fs = _reload_fork_safety(monkeypatch, "darwin")
        with patch(
            "multiprocessing.set_start_method",
            side_effect=RuntimeError("context already set"),
        ):
            # Must not propagate the RuntimeError.
            fs.ensure_spawn_on_darwin()

    def test_safe_to_call_multiple_times(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ensure_spawn_on_darwin() can be called multiple times without error."""
        fs = _reload_fork_safety(monkeypatch, "darwin")
        with patch("multiprocessing.set_start_method") as mock_set:
            fs.ensure_spawn_on_darwin()
            fs.ensure_spawn_on_darwin()
        assert mock_set.call_count == 2


# ---------------------------------------------------------------------------
# Wiring tests — serve entrypoints call the guard
# ---------------------------------------------------------------------------


class TestUiServiceMainCallsGuard:
    """services/ui_service/main.py:main() must call ensure_spawn_on_darwin()."""

    def test_guard_is_called(self) -> None:
        """main() calls ensure_spawn_on_darwin() before uvicorn.run()."""
        guard_calls: list[None] = []

        # Build a fake fork_safety module whose ensure_spawn_on_darwin records calls.
        fake_fork_safety = MagicMock()
        fake_fork_safety.ensure_spawn_on_darwin.side_effect = lambda: (
            guard_calls.append(None)
        )

        fake_uvicorn = MagicMock()

        fake_config = MagicMock()
        fake_config.host = "127.0.0.1"
        fake_config.port = 7777
        fake_config.reload = False
        fake_config.log_level = "info"
        fake_config_cls = MagicMock(return_value=fake_config)
        fake_config_cls.from_env.return_value = fake_config

        fake_config_mod = MagicMock()
        fake_config_mod.UIServiceConfig = fake_config_cls

        # Inject our fakes so the lazy imports inside main() see them.
        with patch.dict(
            "sys.modules",
            {
                "claude_mpm.mcp.fork_safety": fake_fork_safety,
                "uvicorn": fake_uvicorn,
                "claude_mpm.services.ui_service.config": fake_config_mod,
            },
        ):
            import claude_mpm.services.ui_service.main as ui_main

            importlib.reload(ui_main)
            ui_main.main()

        assert len(guard_calls) >= 1, (
            "ensure_spawn_on_darwin() was not called by main()"
        )


class TestServeDaemonForegroundCallsGuard:
    """ServeDaemon._run_foreground() must call ensure_spawn_on_darwin()."""

    def test_guard_is_called_before_event_loop(self) -> None:
        """_run_foreground() calls ensure_spawn_on_darwin() before asyncio.run()."""
        import claude_mpm.mcp.fork_safety as fork_safety_mod
        import claude_mpm.services.ui_service.serve_daemon as sd_mod

        guard_called: list[bool] = []

        def _fake_guard() -> None:
            guard_called.append(True)

        async def _noop_async() -> None:
            pass

        # Patch ensure_spawn_on_darwin on the live module object so the relative
        # import inside serve_daemon resolves to our fake.
        with patch.object(fork_safety_mod, "ensure_spawn_on_darwin", _fake_guard):
            # Reload serve_daemon so it re-executes its top-level imports and
            # picks up the patched fork_safety.
            importlib.reload(sd_mod)

            # Construct a minimal ServeDaemon instance without __init__ I/O.
            inst = sd_mod.ServeDaemon.__new__(sd_mod.ServeDaemon)
            inst.host = "127.0.0.1"
            inst.port = 7777
            inst.daemon_mode = False
            inst.channels = []
            inst.project_root = None
            inst.lifecycle = MagicMock()

            # Replace _async_serve so asyncio.run() returns immediately.
            with patch.object(
                sd_mod.ServeDaemon, "_async_serve", return_value=_noop_async()
            ):
                with patch("asyncio.run"):
                    sd_mod.ServeDaemon._run_foreground(inst)

        assert guard_called, (
            "ensure_spawn_on_darwin() was not called by ServeDaemon._run_foreground()"
        )
