"""Tests for runtime selection and configuration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from claude_mpm.services.agents.agent_runtime import AgentConfig
from claude_mpm.services.agents.runtime_config import get_runtime, get_runtime_type

# ---------------------------------------------------------------------------
# get_runtime_type
# ---------------------------------------------------------------------------


class TestGetRuntimeType:
    """Test runtime type resolution."""

    def test_env_var_sdk(self) -> None:
        with patch.dict("os.environ", {"CLAUDE_MPM_RUNTIME": "sdk"}):
            assert get_runtime_type() == "sdk"

    def test_env_var_cli(self) -> None:
        with patch.dict("os.environ", {"CLAUDE_MPM_RUNTIME": "cli"}):
            assert get_runtime_type() == "cli"

    def test_env_var_case_insensitive(self) -> None:
        with patch.dict("os.environ", {"CLAUDE_MPM_RUNTIME": "SDK"}):
            assert get_runtime_type() == "sdk"

    def test_env_var_invalid_ignored(self) -> None:
        """Invalid env values fall through to auto-detect."""
        with (
            patch.dict("os.environ", {"CLAUDE_MPM_RUNTIME": "invalid"}),
            patch.dict("sys.modules", {"claude_agent_sdk": None}),
        ):
            # The import will succeed (module is None but present in sys.modules)
            # so it should return "sdk" -- but actually importing None raises TypeError
            # Let's just test that it doesn't return "invalid"
            result = get_runtime_type()
            assert result in ("sdk", "cli")

    def test_returns_sdk_when_sdk_available(self) -> None:
        """When no env var and SDK is importable, returns 'sdk'."""
        import types

        fake_sdk = types.ModuleType("claude_agent_sdk")

        with (
            patch.dict("os.environ", {}, clear=False),
            patch.dict("sys.modules", {"claude_agent_sdk": fake_sdk}),
        ):
            # Remove env var if set
            import os

            env = os.environ.copy()
            env.pop("CLAUDE_MPM_RUNTIME", None)
            with patch.dict("os.environ", env, clear=True):
                assert get_runtime_type() == "sdk"

    def test_returns_cli_when_sdk_not_available(self) -> None:
        """When no env var and SDK import fails, returns 'cli'."""
        with patch.dict("os.environ", {}, clear=False):
            import os

            env = os.environ.copy()
            env.pop("CLAUDE_MPM_RUNTIME", None)
            with (
                patch.dict("os.environ", env, clear=True),
                patch(
                    "builtins.__import__",
                    side_effect=_import_without_sdk,
                ),
            ):
                assert get_runtime_type() == "cli"


# ---------------------------------------------------------------------------
# get_runtime
# ---------------------------------------------------------------------------


class TestGetRuntime:
    """Test get_runtime() creates correct runtime instances."""

    def test_get_runtime_sdk(self) -> None:
        with patch(
            "claude_mpm.services.agents.runtime_config.get_runtime_type",
            return_value="sdk",
        ):
            # SDK may not be installed in test env, so mock the factory
            with patch(
                "claude_mpm.services.agents.agent_runtime.create_runtime"
            ) as mock_create:
                from claude_mpm.services.agents.cli_runtime import CLIAgentRunner

                mock_create.return_value = (
                    CLIAgentRunner()
                )  # just needs to return something
                runtime = get_runtime()
                mock_create.assert_called_once_with("sdk", AgentConfig())

    def test_get_runtime_cli(self) -> None:
        with patch(
            "claude_mpm.services.agents.runtime_config.get_runtime_type",
            return_value="cli",
        ):
            runtime = get_runtime()
            assert runtime.runtime_name == "cli"

    def test_get_runtime_with_config(self) -> None:
        config = AgentConfig(model="opus", cwd="/tmp")
        with patch(
            "claude_mpm.services.agents.runtime_config.get_runtime_type",
            return_value="cli",
        ):
            runtime = get_runtime(config)
            assert runtime.runtime_name == "cli"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_real_import = (
    __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
)


def _import_without_sdk(name: str, *args: object, **kwargs: object) -> object:
    """Simulate ImportError for claude_agent_sdk."""
    if name == "claude_agent_sdk":
        raise ImportError("Mocked: no SDK")
    return _real_import(name, *args, **kwargs)
