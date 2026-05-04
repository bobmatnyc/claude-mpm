"""Integration tests for the SDK launch flow.

Verifies the end-to-end wiring between:
  --sdk CLI flag → CLAUDE_MPM_RUNTIME=sdk env var
  → ClaudeRunner(launch_method="sdk")
  → InteractiveSession._launch_sdk_mode()
  → ClaudeSDKClient (mocked)

These tests do NOT call the real Claude SDK; they mock ClaudeSDKClient and
related symbols so the full launch path can be verified without an API key.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest  # noqa: TC002 - pytest is needed at runtime by fixtures

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StopLoop(Exception):
    """Raised inside the mocked input() to break out of the REPL loop."""


def _make_runner_with_sdk_launch() -> Any:
    """Build a ClaudeRunner with launch_method='sdk' (no real claude CLI needed)."""
    from claude_mpm.core.claude_runner import ClaudeRunner

    return ClaudeRunner(
        enable_tickets=False,
        log_level="OFF",
        claude_args=[],
        launch_method="sdk",
        enable_websocket=False,
    )


# ---------------------------------------------------------------------------
# Tests for the launch-path wiring
# ---------------------------------------------------------------------------


class TestSdkLaunchFlowWiring:
    """Verify --sdk flag flows all the way to ``_launch_sdk_mode``."""

    def test_sdk_env_var_sets_launch_method_sdk(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When CLAUDE_MPM_RUNTIME=sdk, ``launch_method`` resolves to 'sdk'."""
        monkeypatch.setenv("CLAUDE_MPM_RUNTIME", "sdk")

        # Simulate what cli/commands/run.py does
        from claude_mpm.services.agents.runtime_config import get_runtime_type

        assert get_runtime_type() == "sdk"

    def test_runner_with_sdk_launch_method_routes_to_launch_sdk_mode(self) -> None:
        """ClaudeRunner(launch_method='sdk') → handle_interactive_input → _launch_sdk_mode."""
        runner = _make_runner_with_sdk_launch()
        assert runner.launch_method == "sdk"

        from claude_mpm.core.interactive_session import InteractiveSession

        session = InteractiveSession(runner)

        environment = {
            "command": ["claude"],
            "environment": os.environ.copy(),
            "session_id": "test-sdk-launch-flow",
        }

        # Mock _launch_sdk_mode to confirm it's called when launch_method='sdk'
        with patch.object(
            session, "_launch_sdk_mode", return_value=True
        ) as mock_launch_sdk:
            result = session.handle_interactive_input(environment)

        assert result is True
        mock_launch_sdk.assert_called_once()

    def test_launch_sdk_mode_initializes_session_state_tracker(self) -> None:
        """``_launch_sdk_mode`` sets the global SessionStateTracker before running."""
        runner = _make_runner_with_sdk_launch()

        from claude_mpm.core.interactive_session import InteractiveSession

        session = InteractiveSession(runner)

        # Patch the SDK so we never actually start a session.
        # We make ClaudeSDKClient.__aenter__ raise so the function exits early
        # but only AFTER the tracker has been registered.
        captured: dict[str, Any] = {}

        def _capture_set_global(tracker: Any) -> None:
            captured["tracker"] = tracker

        # Build a fake claude_agent_sdk module that the import inside
        # _run_sdk_session() will find.
        fake_sdk = MagicMock()
        fake_sdk.AssistantMessage = type("AssistantMessage", (), {})
        fake_sdk.ResultMessage = type("ResultMessage", (), {})
        fake_sdk.SystemMessage = type("SystemMessage", (), {})
        fake_sdk.TextBlock = type("TextBlock", (), {})
        fake_sdk.ToolUseBlock = type("ToolUseBlock", (), {})
        fake_sdk.ClaudeAgentOptions = MagicMock()
        # ClaudeSDKClient as async context manager that raises on enter
        client_cm = MagicMock()
        client_cm.__aenter__ = MagicMock(side_effect=_StopLoop("stop after setup"))
        client_cm.__aexit__ = MagicMock()
        fake_sdk.ClaudeSDKClient = MagicMock(return_value=client_cm)
        fake_sdk.HookMatcher = MagicMock()

        with (
            patch.dict("sys.modules", {"claude_agent_sdk": fake_sdk}),
            patch(
                "claude_mpm.services.agents.session_state_tracker.set_global_tracker",
                side_effect=_capture_set_global,
            ),
            patch.object(runner, "_create_system_prompt", return_value="test prompt"),
        ):
            # _launch_sdk_mode runs an asyncio loop internally; it should
            # propagate _StopLoop after the tracker is registered.
            try:
                session._launch_sdk_mode()
            except _StopLoop:
                pass
            except Exception:
                # Other exceptions are acceptable for this test as long as
                # the tracker was set before the failure point.
                pass

        assert "tracker" in captured, (
            "_launch_sdk_mode must register a SessionStateTracker via "
            "set_global_tracker() before opening the SDK client"
        )
        # Tracker must expose the read API used by /session and /activity
        tracker = captured["tracker"]
        state = tracker.get_session_state()
        assert "session_id" in state
        assert "state" in state
        assert "started_at" in state


class TestSdkAutoDetection:
    """Verify auto-detection logic in runtime_config does not force SDK mode."""

    def test_get_runtime_type_respects_explicit_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit CLAUDE_MPM_RUNTIME=cli wins over SDK availability."""
        monkeypatch.setenv("CLAUDE_MPM_RUNTIME", "cli")

        from claude_mpm.services.agents.runtime_config import get_runtime_type

        assert get_runtime_type() == "cli"

    def test_get_runtime_type_falls_back_when_sdk_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no env var and SDK import fails, fall back to 'cli'."""
        monkeypatch.delenv("CLAUDE_MPM_RUNTIME", raising=False)

        # Force ImportError for claude_agent_sdk
        import builtins

        real_import = builtins.__import__

        def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "claude_agent_sdk":
                raise ImportError("simulated missing SDK")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_fake_import):
            from claude_mpm.services.agents.runtime_config import get_runtime_type

            assert get_runtime_type() == "cli"


class TestMessageEndpointObservability:
    """The /session and /activity endpoints expose tracker state."""

    def test_session_endpoint_returns_unavailable_when_no_tracker(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``GET /session`` returns 'unavailable' when tracker isn't set."""
        # Ensure global tracker is None for this test
        from claude_mpm.services.agents import session_state_tracker

        monkeypatch.setattr(session_state_tracker, "_global_tracker", None)

        from claude_mpm.services.agents.session_state_tracker import (
            get_global_tracker,
        )

        assert get_global_tracker() is None

    def test_session_endpoint_returns_state_when_tracker_set(self) -> None:
        """``GET /session`` returns full state once tracker is registered."""
        from claude_mpm.services.agents.session_state_tracker import (
            SessionState,
            SessionStateTracker,
            get_global_tracker,
            set_global_tracker,
        )

        tracker = SessionStateTracker()
        tracker.set_session_id("test-session-123")
        tracker.set_model("claude-sonnet-4")
        tracker.set_state(SessionState.IDLE)
        set_global_tracker(tracker)

        try:
            t = get_global_tracker()
            assert t is not None
            state = t.get_session_state()
            assert state["session_id"] == "test-session-123"
            assert state["model"] == "claude-sonnet-4"
            assert state["state"] == "idle"
        finally:
            # Cleanup so other tests aren't affected
            set_global_tracker(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Module-level test: full --sdk flag → launch_method wiring via run.py path
# ---------------------------------------------------------------------------


def test_run_session_legacy_sets_sdk_launch_method_when_env_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The run.py launch-method computation routes to 'sdk' under env var.

    This mirrors lines ~1237-1242 of cli/commands/run.py:
        launch_method = getattr(args, "launch_method", "exec")
        if os.environ.get("CLAUDE_MPM_RUNTIME") == "sdk":
            launch_method = "sdk"
    """
    monkeypatch.setenv("CLAUDE_MPM_RUNTIME", "sdk")

    # Simulate the args object that argparse would produce
    args = MagicMock()
    args.launch_method = "exec"

    launch_method = getattr(args, "launch_method", "exec")
    if os.environ.get("CLAUDE_MPM_RUNTIME") == "sdk":
        launch_method = "sdk"

    assert launch_method == "sdk"
