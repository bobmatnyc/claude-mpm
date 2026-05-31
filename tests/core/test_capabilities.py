"""Unit tests for src/claude_mpm/core/capabilities.py.

Tests cover agent_teams_active() across all truthy/falsy env-var values and
the unset-variable (default) case.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from claude_mpm.core.capabilities import agent_teams_active

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENV_VAR = "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"


def _with_env(value: str | None):
    """Context manager: set or unset the Agent Teams env var."""
    if value is None:
        return (
            mock.patch.dict(os.environ, {}, clear=False)
            if _ENV_VAR not in os.environ
            else mock.patch.dict(os.environ, {_ENV_VAR: ""})
        )
    return mock.patch.dict(os.environ, {_ENV_VAR: value})


# ---------------------------------------------------------------------------
# Default / unset behaviour
# ---------------------------------------------------------------------------


class TestAgentTeamsActiveDefault:
    """agent_teams_active() must return False when the env var is unset."""

    def test_returns_false_when_unset(self) -> None:
        env_without_var = {k: v for k, v in os.environ.items() if k != _ENV_VAR}
        with mock.patch.dict(os.environ, env_without_var, clear=True):
            assert agent_teams_active() is False

    def test_returns_false_when_empty_string(self) -> None:
        with mock.patch.dict(os.environ, {_ENV_VAR: ""}):
            assert agent_teams_active() is False

    def test_returns_false_when_whitespace_only(self) -> None:
        with mock.patch.dict(os.environ, {_ENV_VAR: "   "}):
            assert agent_teams_active() is False


# ---------------------------------------------------------------------------
# Truthy values
# ---------------------------------------------------------------------------


class TestAgentTeamsActiveTruthy:
    """agent_teams_active() must return True for all recognised truthy strings."""

    @pytest.mark.parametrize(
        "value",
        [
            "1",
            "true",
            "True",
            "TRUE",
            "yes",
            "Yes",
            "YES",
            "on",
            "On",
            "ON",
        ],
    )
    def test_truthy_values(self, value: str) -> None:
        with mock.patch.dict(os.environ, {_ENV_VAR: value}):
            assert agent_teams_active() is True, (
                f"Expected True for {_ENV_VAR}={value!r}"
            )

    def test_truthy_with_leading_trailing_whitespace(self) -> None:
        # strip() is applied; "  1  " should be truthy
        with mock.patch.dict(os.environ, {_ENV_VAR: "  1  "}):
            assert agent_teams_active() is True

    def test_truthy_true_with_whitespace(self) -> None:
        with mock.patch.dict(os.environ, {_ENV_VAR: "  true  "}):
            assert agent_teams_active() is True


# ---------------------------------------------------------------------------
# Falsy values (explicit non-truthy strings)
# ---------------------------------------------------------------------------


class TestAgentTeamsActiveFalsy:
    """agent_teams_active() must return False for non-truthy string values."""

    @pytest.mark.parametrize(
        "value",
        [
            "0",
            "false",
            "False",
            "FALSE",
            "no",
            "No",
            "NO",
            "off",
            "Off",
            "OFF",
            "2",
            "enabled",
            "disabled",
            "maybe",
        ],
    )
    def test_falsy_values(self, value: str) -> None:
        with mock.patch.dict(os.environ, {_ENV_VAR: value}):
            assert agent_teams_active() is False, (
                f"Expected False for {_ENV_VAR}={value!r}"
            )


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


class TestAgentTeamsActiveReturnType:
    """agent_teams_active() must always return a plain bool."""

    def test_returns_bool_when_false(self) -> None:
        env_without_var = {k: v for k, v in os.environ.items() if k != _ENV_VAR}
        with mock.patch.dict(os.environ, env_without_var, clear=True):
            result = agent_teams_active()
            assert isinstance(result, bool)
            assert result is False

    def test_returns_bool_when_true(self) -> None:
        with mock.patch.dict(os.environ, {_ENV_VAR: "1"}):
            result = agent_teams_active()
            assert isinstance(result, bool)
            assert result is True
